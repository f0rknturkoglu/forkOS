import { subColor } from "./financeLabels";

/**
 * Abonelik/marka rozeti: adin bas harfi, marka renginde daire.
 * Abonelik kartlarinda ve yaklasan odemeler listesinde ayni gorunur.
 */
export function SubBadge({ sub, title, size = 24 }: { sub: string | null; title: string; size?: number }) {
  const letter = (title.trim()[0] ?? "?").toLocaleUpperCase("tr");
  return (
    <span
      aria-hidden
      className="flex shrink-0 select-none items-center justify-center rounded-full font-medium text-canvas"
      style={{ background: subColor(sub), width: size, height: size, fontSize: size * 0.46 }}
    >
      {letter}
    </span>
  );
}
