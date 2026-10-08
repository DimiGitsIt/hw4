import { createContext, useContext, useState, type ReactNode } from "react";
import type { ProductCardData } from "../api";

export interface ChatSearchResults {
  query: string;
  products: ProductCardData[];
}

interface ChatSearchContextValue {
  results: ChatSearchResults | null;
  setResults: (results: ChatSearchResults | null) => void;
}

const ChatSearchContext = createContext<ChatSearchContextValue | undefined>(undefined);

export function ChatSearchProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatSearchResults | null>(null);
  return (
    <ChatSearchContext.Provider value={{ results, setResults }}>
      {children}
    </ChatSearchContext.Provider>
  );
}

export function useChatSearch(): ChatSearchContextValue {
  const ctx = useContext(ChatSearchContext);
  if (!ctx) throw new Error("useChatSearch must be used within a ChatSearchProvider");
  return ctx;
}
