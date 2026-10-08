"""Pydantic / PydanticAI types for the shop chatbot."""

from typing import Literal

from pydantic import BaseModel


class ProductCard(BaseModel):
    """The fields the front end needs to render a product card — in the chat panel, on
    the Products page, or on a chat-driven search result grid. Real database fields
    only: no field here is ever invented or guessed."""

    product_id: str
    name: str
    price: float
    image_url: str
    description: str


class ProductLookup(BaseModel):
    """Resolves a customer's product query (name/keyword, e.g. "the navy hoodie") to a
    specific product. `status="found"` means exactly one match; `"ambiguous"` means several
    matched and the agent should ask the customer to pick one from `candidates`;
    `"not_found"` means nothing matched."""

    status: Literal["found", "ambiguous", "not_found"]
    product: ProductCard | None = None
    candidates: list[ProductCard] = []


class ProductDescription(BaseModel):
    product_id: str
    name: str
    description: str


class ProductPrice(BaseModel):
    product_id: str
    name: str
    price: float


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductStock(BaseModel):
    """A product's stock. `sizes` always lists every size we carry for this product, so the
    agent can offer in-stock alternatives if the one asked about is sold out. `requested_size`
    is set when the customer asked about one specific size; `requested_size_exists` is False
    if that size isn't one we carry at all for this product (as opposed to carried but at 0)."""

    product_id: str
    name: str
    sizes: list[SizeStock]
    requested_size: str | None = None
    requested_size_exists: bool = True


class ChatTurn(BaseModel):
    """One prior message in the conversation, as sent by the front end."""

    role: Literal["user", "assistant"]
    content: str


class PageContext(BaseModel):
    """What page the shopper is on, as reported by the front end. `product_id` is only
    trusted as a lookup key — the server re-fetches the real product from the database
    rather than trusting any product details the browser might also send."""

    page: Literal["home", "products", "product", "about", "login", "create_account", "other"]
    product_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []
    page_context: PageContext | None = None


class ChatHistoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = []
    created_at: str


class ChatReply(BaseModel):
    """`searched` is True only when this turn ran a catalogue search (search_products) for
    a general/category request. The front end uses that flag — not just a non-empty
    `products` list — to decide whether to take over the Products page, so a single
    resolved product from a price/stock question doesn't also trigger a page takeover."""

    message: str
    products: list[ProductCard] = []
    searched: bool = False
