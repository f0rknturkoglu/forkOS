import { useQuery } from "@tanstack/react-query";
import { Bell, CalendarClock, Clock } from "lucide-react";
import { api } from "@/core/api";
import { RowList, Section, relativeTime } from "@/core/ui";
import type { Deadline, Followup, Notification } from "@/core/types";
import { dueTiming, entityHref, TodayRow } from "./TodayRow";
import type { TodayRowTone } from "./TodayRow";
import { isCareerDeadline } from "./DeadlinesWidget";

/**
 * Kariyer (P2 §24): yalnız kariyer işleri, kendi yüzeyine bağlı.
 *
 * Üç kaynak TEK listede birleşir, çünkü kullanıcı için bunlar aynı sorunun
 * parçaları ("başvuruda ne bekliyor?"):
 *   1. takip zamanı gelen başvurular  -> /opportunities/followups
 *   2. kariyer bildirimleri           -> /notifications (okunmamış + fırsat)
 *   3. fırsat/mülakat son tarihleri    -> /deadlines (module = opportunity)
 *
 * Genel bildirimler (kaynak sağlığı, medya, yedek) BURADA gösterilmez: üst
 * şeritteki bildirim panelinde kalırlar. Bu kart kariyer işi için vardır.
 *
 * Bağlantı hedefi her zaman anlamlıdır: kaydın kendi rotası varsa orası,
 * yoksa Kariyer yüzeyi ("tümü").
 */

/** Kartta gösterilen en fazla satır. */
const MAX_ROWS = 5;

/** Kariyer yüzeyi: satırın kendi kaydı yoksa buraya gidilir. */
const CAREER_ROUTE = "#/opportunities";

interface CareerItem {
  key: string;
  title: string;
  meta: string;
  tone: TodayRowTone;
  href: string;
  icon: typeof Bell;
  /** 0 = gecikmiş/bugün, 1 = yakın, 2 = tarihsiz. */
  bucket: number;
  /** Aynı kovadaki sıralama için zaman damgası. */
  at: number;
}

/** Fırsat kaydının bildirimi mi? Genel bildirimler panelde kalır. */
function isCareerNotification(row: Notification): boolean {
  return row.entity_type === "opportunity" || row.kind.startsWith("opportunity");
}

export function CareerWidget() {
  const followups = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<Followup[]>("/opportunities/followups"),
    retry: false,
  });
  // Aynı anahtar bildirim paneliyle paylaşılır: ikinci istek doğmaz, panelin
  // 60 sn'lik tazelemesi bu kartı da günceller.
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
    retry: false,
  });
  const deadlines = useQuery({
    queryKey: ["deadlines"],
    queryFn: () => api.get<Deadline[]>("/deadlines"),
    retry: false,
  });

  const followupRows = Array.isArray(followups.data) ? followups.data : [];
  const notificationRows = Array.isArray(notifications.data) ? notifications.data : [];
  const careerDeadlines = (Array.isArray(deadlines.data) ? deadlines.data : []).filter(isCareerDeadline);

  // Aynı kaydın son tarihi listede varsa bildirimi tekrar gösterilmez.
  const covered = new Set([...followupRows.map((row) => row.id), ...careerDeadlines.map((row) => row.entity_id)]);

  const items: CareerItem[] = [
    ...followupRows.map((row) => {
      const timing = dueTiming(row.follow_up_at);
      return {
        key: `followup:${row.id}`,
        title: row.title,
        meta: `${timing.label} · Takip`,
        tone: timing.tone,
        href: CAREER_ROUTE,
        icon: Clock,
        bucket: timing.delta <= 1 ? 0 : 1,
        at: new Date(row.follow_up_at).getTime(),
      };
    }),
    ...careerDeadlines.map((row) => {
      const timing = dueTiming(row.due_at);
      return {
        key: `deadline:${row.entity_id}`,
        title: row.title,
        meta: `${timing.label} · Son tarih`,
        tone: timing.tone,
        href: entityHref(row.type, row.entity_id) ?? CAREER_ROUTE,
        icon: CalendarClock,
        bucket: timing.delta <= 1 ? 0 : 1,
        at: new Date(row.due_at).getTime(),
      };
    }),
    ...notificationRows
      .filter((row) => row.read_at === null && isCareerNotification(row))
      .filter((row) => !(row.entity_id && covered.has(row.entity_id)))
      .map((row) => ({
        key: `notification:${row.id}`,
        title: row.title,
        meta: relativeTime(row.created_at),
        tone: row.importance >= 2 ? ("warn" as const) : ("neutral" as const),
        href: entityHref(row.entity_type, row.entity_id) ?? CAREER_ROUTE,
        icon: Bell,
        bucket: 2,
        at: new Date(row.created_at).getTime(),
      })),
  ].sort((a, b) => a.bucket - b.bucket || a.at - b.at);

  if (items.length === 0) return null;

  const visible = items.slice(0, MAX_ROWS);
  const rest = items.length - visible.length;

  return (
    <Section
      title="Kariyer"
      hint={`${items.length}`}
      action={
        <a href={CAREER_ROUTE} className="text-meta text-accent hover:underline">
          tümü →
        </a>
      }
    >
      <RowList>
        {visible.map((item) => (
          <TodayRow
            key={item.key}
            icon={item.icon}
            title={item.title}
            meta={item.meta}
            tone={item.tone}
            href={item.href}
          />
        ))}
      </RowList>
      {rest > 0 && <p className="border-t border-subtle pt-2 text-meta text-muted">{rest} kayıt daha var.</p>}
    </Section>
  );
}
