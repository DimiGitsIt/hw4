// The fields any product card needs to render — shared by the Products grid and by
// chat-driven search results, so both can use the exact same <ProductCard> component.
export interface ProductCardData {
  product_id: string;
  name: string;
  price: number;
  image_url: string;
  description: string;
}

export interface ProductSummary extends ProductCardData {
  garment_type: string;
  colors: string[];
  in_stock: boolean;
}

export interface InventoryItem {
  size: string;
  quantity: number;
}

export interface ProductDetail extends ProductSummary {
  search_tags: string[];
  inventory: InventoryItem[];
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatReply {
  message: string;
  products: ProductCardData[];
  searched: boolean;
}

export type PageName =
  | "home"
  | "products"
  | "product"
  | "about"
  | "login"
  | "create_account"
  | "other";

export interface PageContext {
  page: PageName;
  product_id?: string;
}

export interface ChatHistoryEntry {
  role: "user" | "assistant";
  content: string;
  products: ProductCardData[];
  created_at: string;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function fetchProducts(): Promise<ProductSummary[]> {
  return fetch("/api/products").then((res) => handle<ProductSummary[]>(res));
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return fetch(`/api/products/${encodeURIComponent(productId)}`).then((res) =>
    handle<ProductDetail>(res),
  );
}

export function sendChatMessage(
  message: string,
  history: ChatTurn[],
  pageContext: PageContext,
): Promise<ChatReply> {
  return fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ message, history, page_context: pageContext }),
  }).then((res) => handle<ChatReply>(res));
}

export function fetchChatHistory(): Promise<ChatHistoryEntry[]> {
  return fetch("/api/chat/history", { credentials: "same-origin" }).then((res) =>
    handle<ChatHistoryEntry[]>(res),
  );
}

export function clearChatHistory(): Promise<void> {
  return fetch("/api/chat/history", { method: "DELETE", credentials: "same-origin" }).then(() => undefined);
}
