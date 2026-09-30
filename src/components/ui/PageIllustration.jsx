// One page illustration (see src/data/pageIllustrations.js), on the
// light card the artwork is flattened onto (.content-illustration in
// pages/ContentPage.css).
export default function PageIllustration({ item, lang, className = "", sizes }) {
  return (
    <figure className={`content-illustration ${className}`.trim()}>
      <img
        src={item.src}
        srcSet={item.srcSet}
        sizes={sizes}
        width={item.width}
        height={item.height}
        alt={item.alt[lang] ?? item.alt.en}
        decoding="async"
      />
    </figure>
  );
}

// Props for an illustration placed beside the page text.
export function asideProps(item) {
  return {
    className: `content-aside${item.portrait ? " content-aside--portrait" : ""}`,
    sizes: "(max-width: 1023px) calc(100vw - 48px), 440px",
  };
}
