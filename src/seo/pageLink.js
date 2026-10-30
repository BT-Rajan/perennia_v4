import { pathForPage } from "./pageMeta.js";

/**
 * Props for an <a> to one of the site's pages: a real href, so search
 * engines can follow it and visitors can open it in a new tab, while a
 * plain click still switches pages in place through `onNavigate`.
 */
export function pageLinkProps(id, lang, onNavigate, afterNavigate) {
  return {
    href: pathForPage(id, lang),
    onClick: (e) => {
      if (!onNavigate || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      afterNavigate?.();
      onNavigate(id);
    },
  };
}
