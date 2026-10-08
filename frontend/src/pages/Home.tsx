import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchProducts, type ProductSummary } from "../api";
import ProductCard from "../components/ProductCard";
import "./Home.css";

export default function Home() {
  const [arrivals, setArrivals] = useState<ProductSummary[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchProducts()
      .then((data) => {
        if (!cancelled) setArrivals(data.slice(0, 4));
      })
      .catch(() => {
        if (!cancelled) setArrivals(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="home">
      <section className="home__hero">
        <div className="container home__hero-inner">
          <div>
            <p className="home__eyebrow">Campus Customs &middot; New Haven, CT</p>
            <h1 className="home__title">Gear that's actually worth wearing around campus.</h1>
            <p className="home__subtitle">
              We stitch together everyday staples and a little Bulldog pride &mdash; hoodies,
              crewnecks, and tees sized and stocked for real students, not just gift shop
              shelves. Pick a style, check the sizes, and we'll have it ready.
            </p>
            <div className="home__cta-row">
              <Link to="/products" className="cc-button cc-button--primary">
                Shop the collection
              </Link>
              <Link to="/about" className="cc-button cc-button--outline home__cta-outline">
                Our story
              </Link>
            </div>
          </div>
          <div className="home__hero-art" aria-hidden="true">
            <div className="home__hero-badge">
              <span className="home__hero-badge-y">Y</span>
              <span>EST. CAMPUS CUSTOMS</span>
            </div>
          </div>
        </div>
      </section>

      <section className="home__features">
        <div className="container home__features-grid">
          <div className="home__feature cc-animate-in">
            <h3>Stocked, not staged</h3>
            <p>Every size you see is checked against real inventory, so what's listed is what's there.</p>
          </div>
          <div className="home__feature cc-animate-in" style={{ animationDelay: "0.08s" }}>
            <h3>Built for the daily grind</h3>
            <p>From early lectures to late-night library runs, the fits are made to actually get worn.</p>
          </div>
          <div className="home__feature cc-animate-in" style={{ animationDelay: "0.16s" }}>
            <h3>Ask before you buy</h3>
            <p>Use the chat in the corner if you want a second opinion on sizing or color before you order.</p>
          </div>
        </div>
      </section>

      {arrivals && arrivals.length > 0 && (
        <section className="home__arrivals">
          <div className="container">
            <span className="varsity-kicker">Fresh Off The Press</span>
            <h2>New arrivals</h2>
            <div className="home__arrivals-grid">
              {arrivals.map((product, i) => (
                <div key={product.product_id} className="cc-animate-in" style={{ animationDelay: `${i * 0.06}s` }}>
                  <ProductCard product={product} />
                </div>
              ))}
            </div>
            <Link to="/products" className="home__arrivals-link">
              See the full collection &rarr;
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
