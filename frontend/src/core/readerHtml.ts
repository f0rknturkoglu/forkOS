/** Inert fragment + HTML allowlist. No active markup, attributes or remote assets survive. */
export function safeReadingUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch {
    return null;
  }
}
export function sanitizeReaderHtml(html: string): string {
  if (typeof document === "undefined") return html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const template = document.createElement("template");
  template.innerHTML = html;
  const result = document.createElement("div");
  const allowed = new Set([
    "P",
    "BR",
    "DIV",
    "SPAN",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "UL",
    "OL",
    "LI",
    "BLOCKQUOTE",
    "PRE",
    "CODE",
    "EM",
    "STRONG",
    "B",
    "I",
    "U",
    "S",
    "HR",
    "TABLE",
    "THEAD",
    "TBODY",
    "TR",
    "TD",
    "TH",
    "A",
    "FIGCAPTION",
  ]);
  const drop = new Set([
    "SCRIPT",
    "STYLE",
    "IFRAME",
    "OBJECT",
    "EMBED",
    "FORM",
    "INPUT",
    "BUTTON",
    "TEXTAREA",
    "SELECT",
    "SVG",
    "MATH",
    "IMG",
    "VIDEO",
    "AUDIO",
    "SOURCE",
    "LINK",
    "META",
    "BASE",
    "TEMPLATE",
  ]);
  const copy = (node: Node, parent: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      parent.appendChild(document.createTextNode(node.textContent ?? ""));
      return;
    }
    if (!(node instanceof HTMLElement) || drop.has(node.tagName)) return;
    const target = allowed.has(node.tagName) ? document.createElement(node.tagName.toLowerCase()) : parent;
    if (target !== parent) {
      if (node.tagName === "A") {
        const raw = node.getAttribute("href");
        const href = safeReadingUrl(raw) || (raw?.startsWith("mailto:") && !/[<>\s]/.test(raw) ? raw : null);
        if (href) {
          (target as HTMLElement).setAttribute("href", href);
          (target as HTMLElement).setAttribute("rel", "noreferrer noopener");
          (target as HTMLElement).setAttribute("target", "_blank");
        }
      }
      parent.appendChild(target);
    }
    for (const child of [...node.childNodes]) copy(child, target);
  };
  for (const child of [...template.content.childNodes]) copy(child, result);
  return result.innerHTML;
}
