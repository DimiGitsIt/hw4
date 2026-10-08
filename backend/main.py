"""Campus Customs backend — serves product data from campus_customs.db."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db
from .agent import get_chat_reply
from .auth import UserPublic, get_current_user, router as auth_router
from .models import ChatHistoryEntry, ChatReply, ChatRequest

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs.db"
PRODUCTS_DIR = PROJECT_ROOT / "data" / "products"

db.ensure_schema()

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


def get_readonly_connection() -> sqlite3.Connection:
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


class InventoryItem(BaseModel):
    size: str
    quantity: int


class ProductSummary(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    image_url: str
    price: float
    in_stock: bool


class ProductDetail(ProductSummary):
    search_tags: list[str]
    inventory: list[InventoryItem]


def row_to_summary(row: sqlite3.Row) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        image_url=f"/api/images/{row['product_id']}",
        price=row["price"],
        in_stock=bool(row["in_stock"]),
    )


@app.get("/api/products", response_model=list[ProductSummary])
def list_products():
    con = get_readonly_connection()
    try:
        rows = con.execute(
            "SELECT c.product_id, c.name, c.garment_type, c.description, c.colors, "
            "c.image_file_path, c.price, "
            "EXISTS(SELECT 1 FROM inventory i WHERE i.product_id = c.product_id AND i.quantity > 0) AS in_stock "
            "FROM catalogue c ORDER BY c.name"
        ).fetchall()
    finally:
        con.close()
    return [row_to_summary(r) for r in rows]


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str):
    con = get_readonly_connection()
    try:
        row = con.execute(
            "SELECT c.product_id, c.name, c.garment_type, c.description, c.colors, "
            "c.search_tags, c.image_file_path, c.price, "
            "EXISTS(SELECT 1 FROM inventory i WHERE i.product_id = c.product_id AND i.quantity > 0) AS in_stock "
            "FROM catalogue c WHERE c.product_id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")

        inventory_rows = con.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
            (product_id,),
        ).fetchall()
    finally:
        con.close()

    summary = row_to_summary(row)
    return ProductDetail(
        **summary.model_dump(),
        search_tags=json.loads(row["search_tags"]),
        inventory=[InventoryItem(size=r["size"], quantity=r["quantity"]) for r in inventory_rows],
    )


@app.get("/api/images/{product_id}")
def get_product_image(product_id: str):
    con = get_readonly_connection()
    try:
        row = con.execute(
            "SELECT image_file_path FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    finally:
        con.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    relative_path = row["image_file_path"]
    if relative_path.startswith("products/"):
        relative_path = relative_path[len("products/"):]

    image_path = (PRODUCTS_DIR / relative_path).resolve()
    if PRODUCTS_DIR.resolve() not in image_path.parents or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path)


@app.get("/api/chat/history", response_model=list[ChatHistoryEntry])
def get_chat_history(user: Optional[UserPublic] = Depends(get_current_user)):
    if user is None:
        return []
    return db.load_chat_history(user.id)


@app.delete("/api/chat/history")
def clear_chat_history(user: Optional[UserPublic] = Depends(get_current_user)):
    if user is not None:
        db.clear_chat_history(user.id)
    return {"message": "Cleared."}


@app.post("/api/chat", response_model=ChatReply)
async def chat(payload: ChatRequest, user: Optional[UserPublic] = Depends(get_current_user)):
    reply = await get_chat_reply(payload.message, payload.history, customer=user, page_context=payload.page_context)
    if user is not None:
        db.save_chat_message(user.id, "user", payload.message)
        db.save_chat_message(user.id, "assistant", reply.message, products=reply.products)
    return reply
