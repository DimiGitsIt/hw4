import { useLocation } from "react-router-dom";
import type { PageContext } from "../api";

export function usePageContext(): PageContext {
  const { pathname } = useLocation();

  const productMatch = pathname.match(/^\/products\/([^/]+)$/);
  if (productMatch) {
    return { page: "product", product_id: decodeURIComponent(productMatch[1]) };
  }

  switch (pathname) {
    case "/":
      return { page: "home" };
    case "/products":
      return { page: "products" };
    case "/about":
      return { page: "about" };
    case "/login":
      return { page: "login" };
    case "/create-account":
      return { page: "create_account" };
    default:
      return { page: "other" };
  }
}
