/**
 * `[[ ]]` yazma yardimcilari — Notlar editoru ile paylasilir.
 *
 * Wikilink ve #etiket AYRISTIRMASI BACKEND'DE yapilir (core/refs.py); burasi
 * yalnizca yazmayi kolaylastirir. Yani editorden gecmeyen bir yol (API'den
 * dogrudan yazma, import) da ayni baglari uretir -- kural tek yerde.
 */

/** Imlecin hemen solunda kapanmamis bir "[[" var mi? Varsa yazilan parca. */
export function openWikilinkQuery(text: string, caret: number): string | null {
  const before = text.slice(0, caret);
  const start = before.lastIndexOf("[[");
  if (start === -1) return null;
  const fragment = before.slice(start + 2);
  // Kapanmis ya da satir atlamis: artik acik bir wikilink degil.
  if (fragment.includes("]]") || fragment.includes("\n")) return null;
  return fragment;
}

/** `[[parca` yerine `[[Baslik]]` koyar; imlecin yeni yerini de doner. */
export function completeWikilink(text: string, caret: number, title: string): { value: string; caret: number } {
  const start = text.slice(0, caret).lastIndexOf("[[");
  if (start === -1) return { value: text, caret };
  const inserted = `[[${title}]]`;
  return {
    value: text.slice(0, start) + inserted + text.slice(caret),
    caret: start + inserted.length,
  };
}
