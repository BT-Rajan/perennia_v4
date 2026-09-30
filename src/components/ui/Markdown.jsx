import "./Markdown.css";
import Button from "./Button.jsx";
import WorkflowChain from "./WorkflowChain.jsx";
import { isSafeHref } from "../../data/siteContent.js";

// ──────────────────────────────────────────────────────────
// Small, dependency-free Markdown renderer for the site's
// content pages (About / Products / Services / Contact / case
// studies). Covers exactly what the copy in src/content/*.md
// needs: headings, paragraphs, unordered/ordered lists,
// blockquotes, a rule, inline bold/italic/links, plus three
// block-level extras for case studies:
//   ![alt](/path.png "caption")         — a figure (root-relative
//                                          or https src only)
//   [[workflow: A → B → C]]             — a WorkflowChain
//   [[cta]]                             — the page's booking CTA,
//                                          only if the page passes
//                                          `cta` ({ label, onClick })
// Not a general-purpose parser — if a page ever needs tables or
// fenced code, reach for a real Markdown library instead of
// extending this by hand.
// ──────────────────────────────────────────────────────────

const IMAGE_BLOCK = /^!\[([^\]]*)\]\(\s*(\S+?)(?:\s+"([^"]*)")?\s*\)$/;
const WORKFLOW_BLOCK = /^\[\[workflow:\s*(.+)\]\]$/;
const CTA_BLOCK = /^\[\[cta\]\]$/;

// Splits a line of text on **bold**, *italic*, and [text](url) and
// returns an array of strings and inline React elements.
function parseInline(text, keyPrefix) {
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  const nodes = [];
  let lastIndex = 0;
  let match;
  let i = 0;

  while ((match = pattern.exec(text))) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(<strong key={`${keyPrefix}-${i++}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("[")) {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      nodes.push(
        <a key={`${keyPrefix}-${i++}`} href={linkMatch[2]} target="_blank" rel="noreferrer">
          {linkMatch[1]}
        </a>
      );
    } else {
      nodes.push(<em key={`${keyPrefix}-${i++}`}>{token.slice(1, -1)}</em>);
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export default function Markdown({ source, cta }) {
  const blocks = source.trim().split(/\n{2,}/);
  const elements = [];

  blocks.forEach((block, bi) => {
    const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return;

    if (lines.length === 1) {
      const image = lines[0].match(IMAGE_BLOCK);
      if (image) {
        const [, alt, src, caption] = image;
        if (isSafeHref(src)) {
          elements.push(
            <figure key={bi} className="markdown-figure">
              <img src={src} alt={alt} loading="lazy" />
              {caption && <figcaption>{caption}</figcaption>}
            </figure>
          );
        }
        return;
      }
      const workflow = lines[0].match(WORKFLOW_BLOCK);
      if (workflow) {
        const stages = workflow[1].split(/\s*(?:→|->)\s*/).filter(Boolean);
        elements.push(<WorkflowChain key={bi} stages={stages} className="markdown-workflow" />);
        return;
      }
      if (CTA_BLOCK.test(lines[0])) {
        if (cta?.label && cta?.onClick) {
          elements.push(
            <div key={bi} className="markdown-cta">
              <Button variant="primary" onClick={cta.onClick}>{cta.label}</Button>
            </div>
          );
        }
        return;
      }
    }

    const isUnordered = lines.every((l) => /^[-*]\s+/.test(l));
    const isOrdered = lines.every((l) => /^\d+\.\s+/.test(l));

    if (isUnordered || isOrdered) {
      const Tag = isOrdered ? "ol" : "ul";
      elements.push(
        <Tag key={bi}>
          {lines.map((l, li) => (
            <li key={li}>{parseInline(l.replace(/^([-*]|\d+\.)\s+/, ""), `li-${bi}-${li}`)}</li>
          ))}
        </Tag>
      );
      return;
    }

    const first = lines[0];
    if (/^###\s+/.test(first)) {
      elements.push(<h3 key={bi}>{parseInline(first.replace(/^###\s+/, ""), `h-${bi}`)}</h3>);
    } else if (/^##\s+/.test(first)) {
      elements.push(<h2 key={bi}>{parseInline(first.replace(/^##\s+/, ""), `h-${bi}`)}</h2>);
    } else if (/^#\s+/.test(first)) {
      elements.push(<h1 key={bi}>{parseInline(first.replace(/^#\s+/, ""), `h-${bi}`)}</h1>);
    } else if (/^>\s?/.test(first)) {
      elements.push(
        <blockquote key={bi}>
          {lines.map((l, li) => (
            <p key={li}>{parseInline(l.replace(/^>\s?/, ""), `bq-${bi}-${li}`)}</p>
          ))}
        </blockquote>
      );
    } else if (/^-{3,}$/.test(first)) {
      elements.push(<hr key={bi} />);
    } else {
      elements.push(<p key={bi}>{parseInline(lines.join(" "), `p-${bi}`)}</p>);
    }
  });

  return <div className="markdown-content">{elements}</div>;
}
