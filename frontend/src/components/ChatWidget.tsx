import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  clearChatHistory,
  fetchChatHistory,
  sendChatMessage,
  type ChatTurn,
  type ProductCardData,
} from "../api";
import { useAuth } from "../auth/AuthContext";
import { useChatSearch } from "../chat/ChatSearchContext";
import { usePageContext } from "../chat/usePageContext";
import "./ChatWidget.css";

interface ChatEntry {
  id: number;
  role: "user" | "assistant";
  text: string;
  products?: ProductCardData[];
}

let nextId = 1;

const GREETING: ChatEntry = {
  id: 0,
  role: "assistant",
  text: "Hi! I'm the Campus Customs assistant. Ask me about products, sizes, or stock.",
};

// Drawn from real categories in the catalogue — see output/harness.md — not invented.
const STARTER_PROMPTS = [
  "What hoodies do you have?",
  "What's your cheapest t-shirt?",
  "Do you have any crewnecks in navy?",
];

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatEntry[]>([GREETING]);
  const { setResults } = useChatSearch();
  const navigate = useNavigate();
  const { user } = useAuth();
  const pageContext = usePageContext();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Reload this account's saved history whenever who's logged in changes (login,
  // logout, or switching accounts) — never show one user's history to another.
  useEffect(() => {
    if (!user) {
      setMessages([GREETING]);
      return;
    }
    let cancelled = false;
    fetchChatHistory()
      .then((history) => {
        if (cancelled) return;
        if (history.length === 0) {
          setMessages([GREETING]);
          return;
        }
        setMessages(
          history.map((entry) => ({
            id: nextId++,
            role: entry.role,
            text: entry.content,
            products: entry.products.length > 0 ? entry.products : undefined,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setMessages([GREETING]);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    const history: ChatTurn[] = messages.map((m) => ({ role: m.role, content: m.text }));
    setMessages((prev) => [...prev, { id: nextId++, role: "user", text: trimmed }]);
    setInput("");
    setIsSending(true);

    try {
      const { message, products, searched } = await sendChatMessage(trimmed, history, pageContext);
      if (searched) {
        setResults({ query: trimmed, products });
        navigate("/products");
      }
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: "assistant", text: message, products: searched ? undefined : products },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void sendMessage(input);
  }

  async function handleClear() {
    if (user) {
      await clearChatHistory();
    }
    setMessages([GREETING]);
  }

  return (
    <div className="chat-widget">
      <div
        className={"chat-widget__panel" + (isOpen ? " chat-widget__panel--open" : "")}
        aria-hidden={!isOpen}
      >
        {isOpen && (
          <>
          <div className="chat-widget__header">
            <div className="chat-widget__header-brand">
              <span className="chat-widget__header-mark">Y</span>
              <span>Campus Customs Chat</span>
            </div>
            <div className="chat-widget__header-actions">
              <button
                type="button"
                className="chat-widget__clear"
                onClick={handleClear}
                title="Clear conversation"
              >
                Clear
              </button>
              <button
                type="button"
                className="chat-widget__close"
                aria-label="Close chat"
                onClick={() => setIsOpen(false)}
              >
                &times;
              </button>
            </div>
          </div>

          <div className="chat-widget__messages">
            {messages.length === 1 && (
              <div className="chat-widget__starters">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="chat-widget__chip"
                    onClick={() => void sendMessage(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`chat-bubble chat-bubble--${m.role}`}>
                {m.text}
                {m.products && m.products.length > 0 && (
                  <div className="chat-bubble__products">
                    {m.products.map((product) => (
                      <Link
                        key={product.product_id}
                        to={`/products/${product.product_id}`}
                        className="chat-product-card"
                        onClick={() => setIsOpen(false)}
                      >
                        <img src={product.image_url} alt={product.name} />
                        <div>
                          <div className="chat-product-card__name">{product.name}</div>
                          <div className="chat-product-card__price">${product.price.toFixed(2)}</div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isSending && (
              <div className="chat-bubble chat-bubble--assistant chat-bubble--pending">
                Typing&hellip;
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chat-widget__input-row" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a product..."
              aria-label="Chat message"
            />
            <button type="submit" className="cc-button cc-button--primary" disabled={isSending}>
              Send
            </button>
          </form>
          </>
        )}
      </div>

      <button
        type="button"
        className="chat-widget__toggle"
        onClick={() => setIsOpen((open) => !open)}
        aria-label={isOpen ? "Close chat" : "Open chat"}
      >
        {isOpen ? "Close" : "Chat"}
      </button>
    </div>
  );
}
