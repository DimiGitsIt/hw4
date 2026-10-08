import { Link } from "react-router-dom";
import type { ProductCardData } from "../api";
import "./ProductCard.css";

// `in_stock` only exists on the normal catalogue listing (ProductSummary) — chat-driven
// search cards use the leaner ProductCardData, so the badge is optional and simply
// doesn't render for those rather than guessing a stock status we don't have.
type CardProduct = ProductCardData & { in_stock?: boolean };

export default function ProductCard({ product }: { product: CardProduct }) {
  const soldOut = product.in_stock === false;

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card__image-wrap">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="product-card__badge product-card__badge--out">Sold out</span>}
      </div>
      <div className="product-card__body">
        <h3 className="product-card__name">{product.name}</h3>
        <p className="product-card__desc">{product.description}</p>
        <div className="product-card__footer">
          <span className="product-card__price">${product.price.toFixed(2)}</span>
          <span className="product-card__cta">View details &rarr;</span>
        </div>
      </div>
    </Link>
  );
}
