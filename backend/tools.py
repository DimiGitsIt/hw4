"""Read-only database tools for the shop chatbot.

Every query here is parameterized SQL against `catalogue` and `inventory` only,
opened read-only — nothing here touches the `users` table, so the agent has
no path to account data, email addresses, or password hashes.

`find_product` resolves a customer's keyword/name into one specific product (handling
no-match and multiple-match cases); `search_products` is its browsing counterpart,
returning every catalogue match for a general/category request. Three narrow tools
each answer one kind of question about a resolved product (description, price,
stock) rather than one tool that returns everything — a customer asking only "how
much is it?" shouldn't require fetching stock data the agent doesn't need, and
keeping them separate gives each tool a precise, single-purpose description for
the model to match against the question actually asked.
"""

import difflib
import json
import re
import sqlite3
from pathlib import Path

from .models import ProductCard, ProductDescription, ProductLookup, ProductPrice, ProductStock, SizeStock

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs.db"

# Grounded in this store's real garment_type values (checked directly against the
# database — see output/harness.md) — not guessed. Maps common shopper words to the
# terms that actually appear in our catalogue text, so "sweatshirt," "hoody," "tee," and
# similar everyday words find real matches instead of a false "we don't sell that."
SEARCH_SYNONYMS: dict[str, list[str]] = {
    "hoody": ["hoodie"],
    "hoodies": ["hoodie"],
    "sweatshirt": ["hoodie", "crewneck"],
    "sweatshirts": ["hoodie", "crewneck"],
    "jumper": ["hoodie", "crewneck"],
    "jumpers": ["hoodie", "crewneck"],
    "pullover": ["hoodie", "crewneck", "pullover"],
    "tee": ["t-shirt"],
    "tees": ["t-shirt"],
    "shirt": ["t-shirt"],
    "shirts": ["t-shirt"],
    "jacket": ["jacket", "fleece", "bomber"],
    "jackets": ["jacket", "fleece", "bomber"],
    "zip up": ["zip"],
    "zip-up": ["zip"],
}


def _get_readonly_connection() -> sqlite3.Connection:
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def _query_catalogue(keyword: str, limit: int) -> list[sqlite3.Row]:
    pattern = f"%{keyword}%"
    con = _get_readonly_connection()
    try:
        return con.execute(
            "SELECT product_id, name, description, image_file_path, price FROM catalogue "
            "WHERE name LIKE ? OR garment_type LIKE ? OR search_tags LIKE ? "
            "ORDER BY name LIMIT ?",
            (pattern, pattern, pattern, limit),
        ).fetchall()
    finally:
        con.close()


def _catalogue_vocabulary() -> set[str]:
    """Every distinct word appearing in real catalogue name/garment_type/search_tags text,
    used only as a target list for typo correction — never a source of new products."""
    con = _get_readonly_connection()
    try:
        rows = con.execute("SELECT name, garment_type, search_tags FROM catalogue").fetchall()
    finally:
        con.close()
    words: set[str] = set()
    for row in rows:
        text = f"{row['name']} {row['garment_type']} {row['search_tags']}".lower()
        words.update(re.findall(r"[a-z']+", text))
    return words


def _search_catalogue(keyword: str, limit: int) -> list[ProductCard]:
    keyword = keyword.strip()
    rows = _query_catalogue(keyword, limit)

    # 1. LIKE does plain substring matching with no stemming, so a plural like "hoodies"
    #    won't match catalogue text that only ever says "hoodie" — strip a trailing "s".
    if not rows and len(keyword) > 3 and keyword.lower().endswith("s"):
        rows = _query_catalogue(keyword[:-1], limit)

    # 2. Try known synonyms for everyday words that aren't our internal garment_type
    #    vocabulary (e.g. "sweatshirt," "hoody," "tee").
    if not rows:
        for synonym in SEARCH_SYNONYMS.get(keyword.lower(), []):
            rows = _query_catalogue(synonym, limit)
            if rows:
                break

    # 3. Last resort: correct small typos by matching against the real words that
    #    actually appear in the catalogue (edit-distance via difflib), then retry with
    #    whichever real word is closest — grounded in actual data, not a guess.
    if not rows:
        vocabulary = _catalogue_vocabulary()
        close = difflib.get_close_matches(keyword.lower(), vocabulary, n=1, cutoff=0.75)
        if close:
            rows = _query_catalogue(close[0], limit)

    return [
        ProductCard(
            product_id=row["product_id"],
            name=row["name"],
            price=row["price"],
            image_url=f"/api/images/{row['product_id']}",
            description=row["description"],
        )
        for row in rows
    ]


def find_product(keyword: str, limit: int = 5) -> ProductLookup:
    """Resolve a customer's product query (e.g. "the navy hoodie") to a specific product
    by matching name, garment type, or search tags. Always call this first to get a
    product_id before calling the description/price/stock tools."""
    cards = _search_catalogue(keyword, limit)
    if not cards:
        return ProductLookup(status="not_found")
    if len(cards) == 1:
        return ProductLookup(status="found", product=cards[0])
    return ProductLookup(status="ambiguous", candidates=cards)


def search_products(keyword: str, limit: int = 12) -> list[ProductCard]:
    """Search the catalogue broadly for a general/category request — a type of garment
    ("hoodies"), a color ("navy"), or any other keyword — when the customer wants to
    browse options rather than ask about one specific product. Returns every match (up
    to limit), including an empty list if nothing matches. For resolving one specific
    named product, use find_product instead."""
    return _search_catalogue(keyword, limit)


def get_product_description(product_id: str) -> ProductDescription | None:
    """Get a product's full description text by its product_id. Returns None if the
    product_id doesn't exist."""
    con = _get_readonly_connection()
    try:
        row = con.execute(
            "SELECT product_id, name, description FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    finally:
        con.close()
    return ProductDescription(**dict(row)) if row else None


def get_product_price(product_id: str) -> ProductPrice | None:
    """Get a product's exact price by its product_id. Returns None if the product_id
    doesn't exist."""
    con = _get_readonly_connection()
    try:
        row = con.execute(
            "SELECT product_id, name, price FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    finally:
        con.close()
    return ProductPrice(**dict(row)) if row else None


def get_product_stock(product_id: str, size: str | None = None) -> ProductStock | None:
    """Get a product's stock by its product_id. Pass `size` (e.g. "M") to check one size;
    omit it to get every size ("what sizes are left?"). Returns None if the product_id
    doesn't exist. If `size` is given but isn't one we carry for this product at all,
    the result's requested_size_exists is False — that's different from the size being
    carried but sold out (quantity 0), which still shows up in `sizes`."""
    con = _get_readonly_connection()
    try:
        product = con.execute(
            "SELECT product_id, name FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if product is None:
            return None
        inventory_rows = con.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
            (product_id,),
        ).fetchall()
    finally:
        con.close()

    sizes = [
        SizeStock(size=row["size"], quantity=row["quantity"], in_stock=row["quantity"] > 0)
        for row in inventory_rows
    ]
    requested_size_exists = True
    if size is not None:
        normalized = size.strip().lower()
        requested_size_exists = any(s.size.lower() == normalized for s in sizes)

    return ProductStock(
        product_id=product["product_id"],
        name=product["name"],
        sizes=sizes,
        requested_size=size,
        requested_size_exists=requested_size_exists,
    )


def get_sold_out_alternatives(product_id: str, limit: int = 5) -> list[ProductCard]:
    """Find other in-stock products in the same category as a sold-out product (or one
    whose requested size is sold out), to offer as alternatives. Returns an empty list if
    the product_id doesn't exist or nothing else in-stock shares its category."""
    con = _get_readonly_connection()
    try:
        original = con.execute(
            "SELECT garment_type FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if original is None:
            return []
        rows = con.execute(
            "SELECT product_id, name, description, image_file_path, price FROM catalogue c "
            "WHERE garment_type = ? AND product_id != ? "
            "AND EXISTS (SELECT 1 FROM inventory i WHERE i.product_id = c.product_id AND i.quantity > 0) "
            "ORDER BY name LIMIT ?",
            (original["garment_type"], product_id, limit),
        ).fetchall()
    finally:
        con.close()

    return [
        ProductCard(
            product_id=row["product_id"],
            name=row["name"],
            price=row["price"],
            image_url=f"/api/images/{row['product_id']}",
            description=row["description"],
        )
        for row in rows
    ]


def get_product_colors(product_id: str) -> list[str] | None:
    """Get the real colors a product is offered in. Used to ground page-context
    injection (e.g. answering "do you have this in pink?") in actual database data."""
    con = _get_readonly_connection()
    try:
        row = con.execute("SELECT colors FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    finally:
        con.close()
    return json.loads(row["colors"]) if row else None
