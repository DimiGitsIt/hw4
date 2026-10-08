import "./About.css";

export default function About() {
  return (
    <div className="container about-page cc-animate-in">
      <span className="varsity-kicker">Our Story</span>
      <h1>About Campus Customs</h1>
      <p className="about-page__lede">
        Campus Customs started as a dorm-room side project: a small batch of hoodies printed
        for a handful of teammates who wanted something sturdier than the bookstore basics.
        Word got around the courtyard faster than we expected, and a few dozen orders later we
        decided to build it into something students could actually count on.
      </p>

      <div className="about-page__grid">
        <section className="about-page__block">
          <h2>What we're about</h2>
          <p>
            We're not trying to out-brand a varsity store. We just want the gear in your closet
            to fit right, hold up through a few years of washes, and actually look like
            something you'd pick for yourself &mdash; not just something with a crest slapped
            on it.
          </p>
        </section>

        <section className="about-page__block">
          <h2>How we stock the shop</h2>
          <p>
            Every item on this site is tracked against our own inventory, size by size. If a
            page says it's in stock, it's because we checked &mdash; not because the listing
            never got updated. When something runs low, you'll see it here before you waste a
            trip finding out in person.
          </p>
        </section>

        <section className="about-page__block">
          <h2>Where we're headed</h2>
          <p>
            We're slowly building out a shopping assistant (you can find the early version in
            the chat bubble in the corner) so you can ask about fit, color, or whether a hoodie
            runs small, instead of digging through every product page yourself.
          </p>
        </section>
      </div>
    </div>
  );
}
