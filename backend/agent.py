"""Builds the Campus Customs shop chatbot.

A PydanticAI `Agent`, wired to the read-only catalogue/inventory tools in `tools.py`,
routed through Portkey to an OpenAI-compatible model. The provider wiring (a raw
`openai.AsyncOpenAI` client pointed at Portkey, wrapped in PydanticAI's `OpenAIProvider`/
`OpenAIResponsesModel`) matches the pattern already used and confirmed working in this
workspace (see Homework 3's agent.py / build_catalogue.py), and was re-verified here
against the actually-installed pydantic-ai version rather than assumed:
https://ai.pydantic.dev/models/openai/ documents the same `OpenAIProvider(openai_client=...)`
shape for routing an OpenAI-compatible model through a custom base_url/gateway.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from . import audit, tools
from .auth import UserPublic
from .models import (
    ChatReply,
    ChatTurn,
    PageContext,
    ProductCard,
    ProductDescription,
    ProductLookup,
    ProductPrice,
    ProductStock,
)

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# Loaded at import time (not just before each request) so a MODEL_NAME override in
# .env is actually in os.environ by the time it's read just below.
load_dotenv(PROJECT_ROOT / ".env")

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
# Overridable via the MODEL_NAME env var; defaults to the workspace's standard model.
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")

MAX_PRODUCT_CARDS = 12

# How many recent chat turns (user + assistant messages combined) get fed to the model
# as conversation context. 10 = roughly the last 5 exchanges — enough for the agent to
# follow up on what was just discussed without the per-turn token cost (and latency)
# of replaying an entire account's history on every message.
MAX_HISTORY_TURNS = 10

# --- Limits (Problem 12) ---
# How many catalogue matches any single search tool call may return, regardless of what
# limit value the model itself asks for — caps cost/latency and keeps replies scannable.
MAX_SEARCH_RESULTS = 12
# How many model requests (one per back-and-forth step with the LLM, including each time
# it calls a tool and gets a result back) one chat message may trigger. Enforced by
# PydanticAI's own UsageLimits — see https://ai.pydantic.dev/agents/#usage-limits.
MAX_MODEL_REQUESTS = 8
# How many tool calls total one chat message may make.
MAX_TOOL_CALLS = 8
# Longest message we'll accept from the browser before even calling the model.
MAX_MESSAGE_LENGTH = 600

FRIENDLY_LIMIT_MESSAGE = (
    "Sorry — that took more back-and-forth than I'm allowed for one message. "
    "Could you ask that as a simpler, more specific question?"
)
FRIENDLY_ERROR_MESSAGE = "Sorry, something went wrong on our end. Please try again."
FRIENDLY_TOO_LONG_MESSAGE = (
    "That message is a bit long for me to work with — could you shorten it and try again?"
)


def _build_context_block(customer: UserPublic | None, page_context: PageContext | None) -> str:
    """Per-turn context injected into the agent's instructions: who it's talking to and
    what page they're on. Both are resolved server-side from the session/database —
    never from anything the browser claims — so this is safe to treat as ground truth."""
    if customer is not None:
        customer_block = (
            f"Logged in as {customer.first_name} {customer.last_name} (email: {customer.email})."
        )
    else:
        customer_block = "This is a guest — no account is logged in. You don't know their name."

    page_block = "The shopper is not currently on a specific product page."
    if page_context and page_context.page == "product" and page_context.product_id:
        pid = page_context.product_id
        description = tools.get_product_description(pid)
        price = tools.get_product_price(pid)
        stock = tools.get_product_stock(pid)
        colors = tools.get_product_colors(pid)
        if description and price and stock:
            sizes_text = ", ".join(
                f"{s.size} ({'in stock: ' + str(s.quantity) if s.in_stock else 'sold out'})"
                for s in stock.sizes
            )
            page_block = (
                f'The shopper is viewing the product page for "{description.name}" '
                f"(product_id={pid}).\n"
                f"Description: {description.description}\n"
                f"Price: ${price.price:.2f}\n"
                f"Colors available: {', '.join(colors) if colors else 'none listed'}\n"
                f"Stock by size: {sizes_text}\n"
                'If they say "this" or "it", they mean this product.'
            )
        else:
            page_block = "The shopper's page names a product_id that no longer exists in the catalogue."

    return f"## Current customer\n{customer_block}\n\n## Current page\n{page_block}"


def _summarize(value) -> str:
    """Short, human-readable version of a tool result for the audit trail — never the
    full chat message, never anything from the users table."""
    if value is None:
        return "none"
    if hasattr(value, "model_dump_json"):
        text = value.model_dump_json()
    elif isinstance(value, list):
        if value and hasattr(value[0], "model_dump"):
            text = f"{len(value)} result(s): " + ", ".join(
                getattr(v, "product_id", "?") for v in value[:5]
            )
        else:
            text = str(value)
    else:
        text = str(value)
    return text if len(text) <= 200 else text[:197] + "..."


def _make_client() -> AsyncOpenAI:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the project's .env file")
    return AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-provider": "openai"},
        max_retries=4,
        timeout=60,
    )


def _build_agent(
    found_products: list[ProductCard],
    searched_flag: list[bool],
    customer: UserPublic | None,
    page_context: PageContext | None,
    request_id: str,
    user_id: int | None,
) -> Agent:
    """Each call builds a fresh agent whose tools append any product they touch to
    `found_products`, so the API layer can hand the front end exact tool results
    instead of trusting the model to restate ids/prices/images correctly. `searched_flag`
    is flipped True only by search_products, so the front end can tell a real catalogue
    search apart from a single product resolved for a price/stock question. `customer`
    and `page_context` are baked into the instructions for this one turn — a simple,
    explicit alternative to typed PydanticAI deps that needed no change to the existing
    plain-tool wiring."""
    model = OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=_make_client()))
    instructions = (
        PROMPT_PATH.read_text(encoding="utf-8") + "\n\n" + _build_context_block(customer, page_context)
    )
    agent = Agent(model, instructions=instructions, retries=2)

    def _log(tool: str, args: dict, result) -> None:
        audit.append_entry(
            request_id=request_id,
            tool=tool,
            args=args,
            result_summary=_summarize(result),
            user_id=user_id,
        )

    @agent.tool_plain
    def find_product(keyword: str, limit: int = 5) -> ProductLookup:
        """Resolve a customer's product query (e.g. "the navy hoodie") to a specific
        product_id. Always call this first — it may come back "found" (one match),
        "ambiguous" (ask the customer to pick from candidates), or "not_found"."""
        limit = min(limit, MAX_SEARCH_RESULTS)
        result = tools.find_product(keyword, limit)
        if result.status == "found" and result.product:
            found_products.append(result.product)
        elif result.status == "ambiguous":
            found_products.extend(result.candidates)
        _log("find_product", {"keyword": keyword, "limit": limit}, result)
        return result

    @agent.tool_plain
    def search_products(keyword: str, limit: int = 12) -> list[ProductCard]:
        """Search broadly for a general/category request — a garment type ("hoodies"), a
        color, or any browsing keyword — when the customer wants to see options rather
        than resolve one specific product. The matches are shown to the customer as cards
        on the page, so don't re-list every match's details in your reply text — a short
        sentence is enough. Returns an empty list (not an error) if nothing matches."""
        limit = min(limit, MAX_SEARCH_RESULTS)
        results = tools.search_products(keyword, limit)
        found_products.extend(results)
        searched_flag[0] = True
        _log("search_products", {"keyword": keyword, "limit": limit}, results)
        return results

    @agent.tool_plain
    def get_product_description(product_id: str) -> ProductDescription | None:
        """Get a product's full description by its product_id."""
        result = tools.get_product_description(product_id)
        _log("get_product_description", {"product_id": product_id}, result)
        return result

    @agent.tool_plain
    def get_product_price(product_id: str) -> ProductPrice | None:
        """Get a product's exact price by its product_id. Always call this before
        answering a price question — never answer from memory."""
        result = tools.get_product_price(product_id)
        _log("get_product_price", {"product_id": product_id}, result)
        return result

    @agent.tool_plain
    def get_product_stock(product_id: str, size: str | None = None) -> ProductStock | None:
        """Get a product's stock by its product_id. Pass `size` (e.g. "M") for one size,
        or omit it for every size. Always call this before answering a stock question —
        never answer from memory."""
        result = tools.get_product_stock(product_id, size)
        _log("get_product_stock", {"product_id": product_id, "size": size}, result)
        return result

    @agent.tool_plain
    def get_sold_out_alternatives(product_id: str, limit: int = 5) -> list[ProductCard]:
        """Call this right after telling the customer a product or size is sold out, to
        find other in-stock products in the same category to offer instead. Always state
        the sold-out fact first in your reply, then present these as alternatives — never
        lead with the alternatives. Returns an empty list if there's nothing comparable."""
        limit = min(limit, MAX_SEARCH_RESULTS)
        results = tools.get_sold_out_alternatives(product_id, limit)
        found_products.extend(results)
        _log("get_sold_out_alternatives", {"product_id": product_id, "limit": limit}, results)
        return results

    return agent


def _to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


async def get_chat_reply(
    message: str,
    history: list[ChatTurn],
    customer: UserPublic | None = None,
    page_context: PageContext | None = None,
) -> ChatReply:
    request_id = uuid.uuid4().hex[:12]
    user_id = customer.id if customer else None

    if len(message) > MAX_MESSAGE_LENGTH:
        audit.append_entry(
            request_id=request_id,
            tool=None,
            stop_reason="message_too_long",
            user_id=user_id,
        )
        return ChatReply(message=FRIENDLY_TOO_LONG_MESSAGE, products=[], searched=False)

    found_products: list[ProductCard] = []
    searched_flag = [False]
    agent = _build_agent(found_products, searched_flag, customer, page_context, request_id, user_id)
    recent_history = history[-MAX_HISTORY_TURNS:]
    usage_limits = UsageLimits(request_limit=MAX_MODEL_REQUESTS, tool_calls_limit=MAX_TOOL_CALLS)

    try:
        result = await agent.run(
            message,
            message_history=_to_message_history(recent_history),
            usage_limits=usage_limits,
        )
    except UsageLimitExceeded as exc:
        audit.append_entry(
            request_id=request_id, tool=None, stop_reason=f"usage_limit_exceeded: {exc}", user_id=user_id
        )
        return ChatReply(message=FRIENDLY_LIMIT_MESSAGE, products=[], searched=False)
    except Exception as exc:  # noqa: BLE001 — any model/tool failure still needs a friendly reply + audit entry
        audit.append_entry(
            request_id=request_id, tool=None, stop_reason=f"error: {exc}", user_id=user_id
        )
        return ChatReply(message=FRIENDLY_ERROR_MESSAGE, products=[], searched=False)

    audit.append_entry(request_id=request_id, tool=None, stop_reason="completed", user_id=user_id)

    unique_products: dict[str, ProductCard] = {}
    for product in found_products:
        unique_products[product.product_id] = product

    return ChatReply(
        message=result.output,
        products=list(unique_products.values())[:MAX_PRODUCT_CARDS],
        searched=searched_flag[0],
    )
