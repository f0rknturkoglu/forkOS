/**
 * Kucuk markdown ayristiricisi -- notlar icin.
 *
 * Neden kendi ayristiricimiz: render HTML URETMEZ, React dugumu uretir
 * (Markdown.tsx). Yani `dangerouslySetInnerHTML` yok, dolayisiyla XSS yuzeyi
 * de yok; sanitizer bagimliligina gerek kalmiyor ve giris paketi buyumuyor.
 * Desteklenen alt kume bilerek dar: baslik, kalin/italik, kod, liste, alinti,
 * yatay cizgi, baglanti, [[wikilink]] ve #etiket.
 *
 * Ayristirici SAF: DOM'a, React'e ya da ag'a dokunmaz -- testi kolay.
 */

export type Inline =
  | { t: "text"; v: string }
  | { t: "code"; v: string }
  | { t: "strong"; v: Inline[] }
  | { t: "em"; v: Inline[] }
  | { t: "strike"; v: Inline[] }
  | { t: "link"; label: string; href: string }
  | { t: "wiki"; target: string; label: string }
  | { t: "tag"; name: string };

export type Block =
  | { t: "heading"; level: number; content: Inline[] }
  | { t: "paragraph"; content: Inline[] }
  | { t: "quote"; content: Inline[][] }
  | { t: "list"; ordered: boolean; items: Inline[][] }
  | { t: "tasks"; items: { checked: boolean; content: Inline[] }[] }
  | { t: "code"; lang: string | null; v: string }
  | { t: "hr" };

/** Yalniz bu semalara izin verilir -- `javascript:` baglanti asla uretilmez. */
const SAFE_SCHEME = /^(https?:\/\/|mailto:|\/|#)/i;

export function safeHref(raw: string): string | null {
  const href = raw.trim();
  if (!href || !SAFE_SCHEME.test(href)) return null;
  return href;
}

/* ── Satir ici ──────────────────────────────────────────────────────── */

// Sira onemli: kod once (icindeki isaretler yorumlanmasin), sonra wikilink,
// baglanti, kalin, italik, ustu cizili, etiket, ciplak URL.
const INLINE = new RegExp(
  [
    "(`[^`\\n]+`)", // 1 kod
    "(\\[\\[[^\\[\\]\\n]+?\\]\\])", // 2 wikilink
    "(!?\\[[^\\]\\n]*\\]\\([^)\\s]+\\))", // 3 baglanti
    "(\\*\\*[^*\\n]+\\*\\*|__[^_\\n]+__)", // 4 kalin
    "(\\*[^*\\n]+\\*|_[^_\\n]+_)", // 5 italik
    "(~~[^~\\n]+~~)", // 6 ustu cizili
    "((?<![\\w#/=])#[A-Za-zÇĞİÖŞÜçğıöşü][\\w\\-çğıöşüÇĞİÖŞÜ]{0,63})", // 7 etiket
    "(https?://[^\\s<>()]+)", // 8 ciplak URL
  ].join("|"),
  "gu",
);

export function parseInline(source: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  const push = (value: string) => {
    if (value) out.push({ t: "text", v: value });
  };

  for (const match of source.matchAll(INLINE)) {
    const index = match.index ?? 0;
    push(source.slice(last, index));
    const [raw, code, wiki, linkRaw, strong, em, strike, tag, bare] = match;
    if (code) {
      out.push({ t: "code", v: code.slice(1, -1) });
    } else if (wiki) {
      const inner = wiki.slice(2, -2);
      const pipe = inner.indexOf("|");
      const target = (pipe === -1 ? inner : inner.slice(0, pipe)).trim();
      const label = (pipe === -1 ? inner : inner.slice(pipe + 1)).trim() || target;
      out.push({ t: "wiki", target, label });
    } else if (linkRaw) {
      const cut = linkRaw.indexOf("](");
      const label = linkRaw.slice(linkRaw.indexOf("[") + 1, cut);
      const href = safeHref(linkRaw.slice(cut + 2, -1));
      // Guvensiz sema: baglanti degil duz metin olarak kalir.
      if (href) out.push({ t: "link", label: label || href, href });
      else push(linkRaw);
    } else if (strong) {
      out.push({ t: "strong", v: parseInline(strong.slice(2, -2)) });
    } else if (em) {
      out.push({ t: "em", v: parseInline(em.slice(1, -1)) });
    } else if (strike) {
      out.push({ t: "strike", v: parseInline(strike.slice(2, -2)) });
    } else if (tag) {
      out.push({ t: "tag", name: tag.slice(1) });
    } else if (bare) {
      out.push({ t: "link", label: bare, href: bare });
    }
    last = index + raw.length;
  }
  push(source.slice(last));
  return out;
}

/* ── Blok ───────────────────────────────────────────────────────────── */

const HEADING = /^(#{1,6})\s+(.*)$/;
const TASK = /^[-*+]\s+\[([ xX])\]\s+(.*)$/;
const BULLET = /^[-*+]\s+(.*)$/;
const ORDERED = /^\d{1,3}[.)]\s+(.*)$/;
const QUOTE = /^>\s?(.*)$/;
const HR = /^\s*([-*_])(\s*\1){2,}\s*$/;
const FENCE = /^```\s*(\S+)?\s*$/;

export function parseMarkdown(source: string): Block[] {
  const lines = (source ?? "").replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let paragraph: string[] = [];

  const flush = () => {
    if (paragraph.length) {
      blocks.push({ t: "paragraph", content: parseInline(paragraph.join(" ").trim()) });
      paragraph = [];
    }
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];

    const fence = line.match(FENCE);
    if (fence) {
      flush();
      const body: string[] = [];
      i += 1;
      while (i < lines.length && !/^```/.test(lines[i])) {
        body.push(lines[i]);
        i += 1;
      }
      blocks.push({ t: "code", lang: fence[1] ?? null, v: body.join("\n") });
      continue;
    }

    if (!line.trim()) {
      flush();
      continue;
    }
    if (HR.test(line)) {
      flush();
      blocks.push({ t: "hr" });
      continue;
    }

    const heading = line.match(HEADING);
    if (heading) {
      flush();
      blocks.push({
        t: "heading",
        level: heading[1].length,
        content: parseInline(heading[2].trim()),
      });
      continue;
    }

    // Gorev listesi duz listeden ONCE denenir ("- [ ] x" ikisine de uyar).
    if (TASK.test(line)) {
      flush();
      const items: { checked: boolean; content: Inline[] }[] = [];
      while (i < lines.length) {
        const match = lines[i].match(TASK);
        if (!match) break;
        items.push({ checked: match[1].toLowerCase() === "x", content: parseInline(match[2]) });
        i += 1;
      }
      i -= 1;
      blocks.push({ t: "tasks", items });
      continue;
    }

    const listMatch = line.match(BULLET) ?? line.match(ORDERED);
    if (listMatch) {
      flush();
      const ordered = ORDERED.test(line);
      const items: Inline[][] = [];
      while (i < lines.length) {
        const current = lines[i];
        if (TASK.test(current)) break;
        const match = ordered ? current.match(ORDERED) : current.match(BULLET);
        if (!match) break;
        items.push(parseInline(match[1]));
        i += 1;
      }
      i -= 1;
      blocks.push({ t: "list", ordered, items });
      continue;
    }

    const quote = line.match(QUOTE);
    if (quote) {
      flush();
      const rows: Inline[][] = [];
      while (i < lines.length) {
        const match = lines[i].match(QUOTE);
        if (!match) break;
        rows.push(parseInline(match[1]));
        i += 1;
      }
      i -= 1;
      blocks.push({ t: "quote", content: rows });
      continue;
    }

    paragraph.push(line.trim());
  }
  flush();
  return blocks;
}

/** Govdedeki [[hedef]] basliklari -- editor onizlemesi ve backend ayni kurali kullanir. */
export function wikilinkTargets(source: string): string[] {
  const seen = new Set<string>();
  for (const block of parseMarkdown(source)) {
    const walk = (nodes: Inline[]) => {
      for (const node of nodes) {
        if (node.t === "wiki") seen.add(node.target);
        else if (node.t === "strong" || node.t === "em" || node.t === "strike") walk(node.v);
      }
    };
    if (block.t === "heading" || block.t === "paragraph") walk(block.content);
    else if (block.t === "list") block.items.forEach(walk);
    else if (block.t === "tasks") block.items.forEach((item) => walk(item.content));
    else if (block.t === "quote") block.content.forEach(walk);
  }
  return [...seen];
}
