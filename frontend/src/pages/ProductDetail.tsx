import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchProduct, type ProductDetail as ProductDetailData } from "../api";
import "./ProductDetail.css";

const LOW_STOCK_THRESHOLD = 15;

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<ProductDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    let cancelled = false;
    setProduct(null);
    setError(null);
    setSelectedSize(null);
    fetchProduct(productId)
      .then((data) => {
        if (!cancelled) setProduct(data);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't find that product.");
      });
    return () => {
      cancelled = true;
    };
  }, [productId]);

  if (error) {
    return (
      <div className="container product-detail-page">
        <p className="product-detail-page__error">{error}</p>
        <Link to="/products" className="cc-button cc-button--outline">
          &larr; Back to products
        </Link>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="container product-detail-page">
        <p>Loading product...</p>
      </div>
    );
  }

  const totalStock = product.inventory.reduce((sum, item) => sum + item.quantity, 0);
  const stockStatus =
    totalStock === 0 ? "out" : totalStock <= LOW_STOCK_THRESHOLD ? "low" : "healthy";

  return (
    <div className="container product-detail-page">
      <Link to="/products" className="product-detail-page__back">
        &larr; Back to products
      </Link>

      <div className="product-detail cc-animate-in">
        <div className="product-detail__image-wrap">
          <img src={product.image_url} alt={product.name} />
          {stockStatus === "out" && (
            <span className="product-card__badge product-card__badge--out">Sold out</span>
          )}
          {stockStatus === "low" && (
            <span className="product-card__badge product-card__badge--low">Low stock</span>
          )}
        </div>

        <div className="product-detail__info">
          <p className="product-detail__type">{product.garment_type}</p>
          <h1>{product.name}</h1>

          <div className="product-detail__price-row">
            <span className="product-detail__price">${product.price.toFixed(2)}</span>
            {stockStatus === "healthy" && (
              <span className="product-detail__status product-detail__status--in">In stock</span>
            )}
            {stockStatus === "low" && (
              <span className="product-detail__status product-detail__status--low">
                Low stock — going fast
              </span>
            )}
            {stockStatus === "out" && (
              <span className="product-detail__status product-detail__status--out">
                Currently sold out
              </span>
            )}
          </div>

          <p className="product-detail__desc">{product.description}</p>

          <div className="product-detail__colors">
            <h3>Colors</h3>
            <div className="product-detail__tag-row">
              {product.colors.map((color) => (
                <span key={color} className="product-detail__tag">
                  {color}
                </span>
              ))}
            </div>
          </div>

          <div className="product-detail__sizes">
            <h3>Size</h3>
            <div className="size-picker">
              {product.inventory.map((item) => {
                const soldOut = item.quantity === 0;
                const isSelected = selectedSize === item.size;
                return (
                  <button
                    key={item.size}
                    type="button"
                    disabled={soldOut}
                    className={
                      "size-picker__chip" +
                      (isSelected ? " size-picker__chip--selected" : "") +
                      (soldOut ? " size-picker__chip--disabled" : "")
                    }
                    onClick={() => setSelectedSize(item.size)}
                    title={soldOut ? `${item.size} — sold out` : `${item.size} — ${item.quantity} left`}
                  >
                    {item.size}
                  </button>
                );
              })}
            </div>
            <p className="size-picker__hint">
              {selectedSize
                ? (() => {
                    const match = product.inventory.find((i) => i.size === selectedSize);
                    return match && match.quantity > 0
                      ? `${match.quantity} left in size ${selectedSize}.`
                      : `Size ${selectedSize} is sold out.`;
                  })()
                : "Select a size to check exact stock."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
