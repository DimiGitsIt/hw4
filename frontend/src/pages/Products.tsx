import { useEffect, useMemo, useState } from "react";
import { fetchProducts, type ProductSummary } from "../api";
import { useChatSearch } from "../chat/ChatSearchContext";
import ProductCard from "../components/ProductCard";
import "./Products.css";

type SortOption = "name" | "price-asc" | "price-desc";

const DEFAULT_FILTERS = {
  category: "all",
  minPrice: "",
  maxPrice: "",
  inStockOnly: false,
  sortBy: "name" as SortOption,
};

export default function Products() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { results, setResults } = useChatSearch();

  const [category, setCategory] = useState(DEFAULT_FILTERS.category);
  const [minPrice, setMinPrice] = useState(DEFAULT_FILTERS.minPrice);
  const [maxPrice, setMaxPrice] = useState(DEFAULT_FILTERS.maxPrice);
  const [inStockOnly, setInStockOnly] = useState(DEFAULT_FILTERS.inStockOnly);
  const [sortBy, setSortBy] = useState<SortOption>(DEFAULT_FILTERS.sortBy);

  useEffect(() => {
    let cancelled = false;
    fetchProducts()
      .then((data) => {
        if (!cancelled) setProducts(data);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load products right now. Please try again shortly.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const categories = useMemo(() => {
    if (!products) return [];
    return Array.from(new Set(products.map((p) => p.garment_type))).sort();
  }, [products]);

  const visibleProducts = useMemo(() => {
    if (!products) return [];
    const min = minPrice.trim() === "" ? null : Number(minPrice);
    const max = maxPrice.trim() === "" ? null : Number(maxPrice);

    const filtered = products.filter((p) => {
      if (category !== "all" && p.garment_type !== category) return false;
      if (min !== null && !Number.isNaN(min) && p.price < min) return false;
      if (max !== null && !Number.isNaN(max) && p.price > max) return false;
      if (inStockOnly && !p.in_stock) return false;
      return true;
    });

    const sorted = [...filtered];
    if (sortBy === "price-asc") sorted.sort((a, b) => a.price - b.price);
    else if (sortBy === "price-desc") sorted.sort((a, b) => b.price - a.price);
    else sorted.sort((a, b) => a.name.localeCompare(b.name));
    return sorted;
  }, [products, category, minPrice, maxPrice, inStockOnly, sortBy]);

  function resetFilters() {
    setCategory(DEFAULT_FILTERS.category);
    setMinPrice(DEFAULT_FILTERS.minPrice);
    setMaxPrice(DEFAULT_FILTERS.maxPrice);
    setInStockOnly(DEFAULT_FILTERS.inStockOnly);
    setSortBy(DEFAULT_FILTERS.sortBy);
  }

  if (results) {
    return (
      <div className="container products-page">
        <div className="chat-results-banner">
          <span>
            Showing results for the chat: <strong>&ldquo;{results.query}&rdquo;</strong>
          </span>
          <button
            type="button"
            className="cc-button cc-button--outline"
            onClick={() => setResults(null)}
          >
            Clear &amp; show full catalogue
          </button>
        </div>

        {results.products.length > 0 ? (
          <div className="products-grid">
            {results.products.map((product) => (
              <ProductCard key={product.product_id} product={product} />
            ))}
          </div>
        ) : (
          <div className="products-page__empty">
            <p>No matches found for &ldquo;{results.query}&rdquo;.</p>
            <p>Try a different search in chat, or browse the full catalogue below.</p>
          </div>
        )}
      </div>
    );
  }

  const resultCount = products
    ? visibleProducts.length === products.length
      ? `${products.length} styles available`
      : `${visibleProducts.length} of ${products.length} styles match`
    : null;

  return (
    <div className="container products-page">
      <div className="products-page__header">
        <span className="varsity-kicker">Full Collection</span>
        <h1>Shop All</h1>
        <p className="products-page__lede">
          Every style we carry, checked against real stock — filter it down to what
          you actually want.
        </p>
      </div>

      {error && <p className="products-page__error">{error}</p>}

      {products && (
        <>
          <div className="products-filters cc-animate-in">
            <div className="products-filters__field">
              <label htmlFor="filter-category">Category</label>
              <select
                id="filter-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="all">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="products-filters__field">
              <label htmlFor="filter-min-price">Min price</label>
              <input
                id="filter-min-price"
                type="number"
                min={0}
                placeholder="$0"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
              />
            </div>

            <div className="products-filters__field">
              <label htmlFor="filter-max-price">Max price</label>
              <input
                id="filter-max-price"
                type="number"
                min={0}
                placeholder="Any"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
              />
            </div>

            <div className="products-filters__field products-filters__field--checkbox">
              <label htmlFor="filter-in-stock">
                <input
                  id="filter-in-stock"
                  type="checkbox"
                  checked={inStockOnly}
                  onChange={(e) => setInStockOnly(e.target.checked)}
                />
                In stock only
              </label>
            </div>

            <div className="products-filters__field">
              <label htmlFor="filter-sort">Sort by</label>
              <select
                id="filter-sort"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
              >
                <option value="name">Name (A–Z)</option>
                <option value="price-asc">Price: low to high</option>
                <option value="price-desc">Price: high to low</option>
              </select>
            </div>

            <button type="button" className="cc-button cc-button--outline" onClick={resetFilters}>
              Reset
            </button>
          </div>

          <p className="products-page__count">{resultCount}</p>

          {visibleProducts.length > 0 ? (
            <div className="products-grid">
              {visibleProducts.map((product, i) => (
                <div
                  key={product.product_id}
                  className="cc-animate-in"
                  style={{ animationDelay: `${Math.min(i, 10) * 0.035}s` }}
                >
                  <ProductCard product={product} />
                </div>
              ))}
            </div>
          ) : (
            <div className="products-page__empty">
              <p>No products match your filters.</p>
              <p>Try widening your price range or clearing a filter.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
