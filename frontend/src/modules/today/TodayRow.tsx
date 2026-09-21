import type { LucideIcon } from "lucide-react";
import { entityRoute } from "@/core/entityRegistry";
import { cx } from "@/core/ui";
import { daysBetween, localDateKey, todayKey } from "@/lib/date";

/**
 * Home kartlarının (Son tarihler, Kariyer) ortak satırı.
 *
 * Satır ya bir hedefe gider ya da gitmez; ikisi AYNI görünmez. Hedefi olmayan
 * satır düz metindir -- kullanıcıyı boşa tıklatan bir bağlantı çizilmez.
 */

export type TodayRowTone = "danger" | "warn" | "neutral";

const TONE_CLASS: Record<TodayRowTone, string> = {
  danger: "text-danger",
  warn: "text-warn",
  neutral: "text-muted",
};

export function TodayRow({
  icon: Icon,
  title,
  meta,
  tone = "neutral",
  href,
}: {
  icon: LucideIcon;
  title: string;
  /** Zamanlama ya da kaynak: satırın altındaki tek satır. */
  meta: string;
  tone?: TodayRowTone;
  href?: string | null;
}) {
  const body = (
    <>
      <Icon size={14} className={cx("mt-0.5 shrink-0", TONE_CLASS[tone])} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-body text-primary">{title}</span>
        <span className="mt-0.5 block text-meta text-muted">{meta}</span>
      </span>
    </>
  );
  return href ? (
    <a href={href} title={title} className="flex items-start gap-2.5 py-2 hover:text-accent">
      {body}
    </a>
  ) : (
    <div className="flex items-start gap-2.5 py-2">{body}</div>
  );
}

/**
 * Kaydın kendi rotası. Kayıt defteri tipi tanımıyorsa (henüz hidratlanmamış
 * ya da bilinmeyen tip) `null` döner: ölü bir bağlantı çizmek yerine satır düz
 * metin olur.
 */
export function entityHref(type: string | null | undefined, id: string | null | undefined): string | null {
  if (!type || !id) return null;
  const route = entityRoute(type, id);
  // Kayit defteri "{id}"siz rota verirse (kok ya da taninmayan tip) hedef yoktur.
  if (route === "#/" || route === "/") return null;
  return route.startsWith("#") ? route : `#${route}`;
}

/**
 * Bir son tarihin bugüne göre okunur etiketi + rengi: gecikmiş kırmızı,
 * bugün sarı, ileri tarih nötr. Kısa "T-3" yerine cümle: kart bir karar
 * yüzeyi, bulmaca değil.
 */
export function dueTiming(iso: string, today = todayKey()): { label: string; tone: TodayRowTone; delta: number } {
  const delta = daysBetween(today, localDateKey(new Date(iso)));
  if (delta < 0) return { label: `${-delta} gün gecikti`, tone: "danger", delta };
  if (delta === 0) return { label: "Bugün", tone: "warn", delta };
  if (delta === 1) return { label: "Yarın", tone: "neutral", delta };
  return { label: `${delta} gün kaldı`, tone: "neutral", delta };
}
