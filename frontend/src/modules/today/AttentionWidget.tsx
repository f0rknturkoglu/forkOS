import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bell, CalendarClock, Clock } from "lucide-react";
import { api } from "@/core/api";
import { entityRoute } from "@/core/entityRegistry";
import { RowList, Section, relativeTime } from "@/core/ui";
import { daysBetween, localDateKey, todayKey } from "@/lib/date";
import type { Deadline, Followup, Notification } from "@/core/types";

/**
 * TEK dikkat yüzeyi (P2 §23).
 *
 * Önceden Home'da dört ayrı widget aynı soruyu farklı parçalarla yanıtlıyordu
 * (son tarihler, takipler, bildirimler, gecikenler). Kullanıcı için soru tek:
 * "şu an neyin farkında olmam gerekiyor?". Bu yüzey o soruyu BİR listede
 * yanıtlar ve bilinçli olarak sınırlıdır.
 *
 * Sınırlar:
 *   - en fazla 5 satır; fazlası sayı olarak bildirilir (sonsuz liste yok),
 *   - boşken hiçbir şey çizilmez (sessizlik başarıdır),
 *   - bir uç hata verirse yalnız o kaynak düşer, kalan veriler dürüstçe gösterilir,
 *   - hiçbir canonical kayıt değiştirilmez; satırlar yalnız gezinir.
 */

const MAX_ROWS = 5;

interface AttentionItem {
  key: string;
  title: string;
  meta: string;
  tone: "danger" | "warn" | "neutral";
  href: string | null;
  /** 0 = gecikmiş/bugün, 1 = yarın ve sonrası, 2 = tarihsiz bildirim. */
  bucket: number;
  /** Aynı gün içindeki sıralama için zaman damgası. */
  at: number;
  icon: typeof Bell;
}

function deadlineItems(rows: Deadline[]): AttentionItem[] {
  const today = todayKey();
  return rows.map((row) => {
    const due = localDateKey(new Date(row.due_at));
    const delta = daysBetween(today, due);
    return {
      key: `deadline:${row.entity_id}`,
      title: row.title,
      meta: delta < 0 ? `${-delta} gün gecikti` : delta === 0 ? "Bugün" : `T-${delta}`,
      tone: delta <= 0 ? "danger" : "warn",
      href: entityRoute(row.type, row.entity_id),
      bucket: delta <= 1 ? 0 : 1,
      at: new Date(row.due_at).getTime(),
      icon: CalendarClock,
    };
  });
}

function followupItems(rows: Followup[]): AttentionItem[] {
  const today = todayKey();
  return rows.map((row) => {
    const due = localDateKey(new Date(row.follow_up_at));
    const delta = daysBetween(today, due);
    return {
      key: `followup:${row.id}`,
      title: row.title,
      meta: delta <= 0 ? "Takip zamanı" : delta === 1 ? "Yarın" : `${delta} gün sonra`,
      tone: delta <= 0 ? "warn" : "neutral",
      href: "#/opportunities",
      bucket: delta <= 1 ? 0 : 1,
      at: new Date(row.follow_up_at).getTime(),
      icon: Clock,
    };
  });
}

function notificationItems(rows: Notification[], mutedFromDeadlines: Set<string>): AttentionItem[] {
  return (
    rows
      .filter((row) => row.read_at === null)
      // Aynı kaydın son tarihi zaten listede: bildirim tekrarı gösterilmez.
      .filter((row) => !(row.entity_id && mutedFromDeadlines.has(row.entity_id)))
      .map((row) => ({
        key: `notification:${row.id}`,
        title: row.title,
        meta: relativeTime(row.created_at),
        tone: row.importance >= 2 ? "warn" : "neutral",
        href: row.entity_id && row.entity_type ? entityRoute(row.entity_type, row.entity_id) : null,
        bucket: 2,
        at: new Date(row.created_at).getTime(),
        icon: Bell,
      }))
  );
}

const TONE_CLASS = {
  danger: "text-danger",
  warn: "text-warn",
  neutral: "text-muted",
} as const;

export function AttentionWidget() {
  const deadlines = useQuery({
    queryKey: ["deadlines"],
    queryFn: () => api.get<Deadline[]>("/deadlines"),
    retry: false,
  });
  const followups = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<Followup[]>("/opportunities/followups"),
    retry: false,
  });
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
    retry: false,
  });

  const deadlineRows = Array.isArray(deadlines.data) ? deadlines.data : [];
  const followupRows = Array.isArray(followups.data) ? followups.data : [];
  const notificationRows = Array.isArray(notifications.data) ? notifications.data : [];

  const mutedIds = new Set(deadlineRows.map((row) => row.entity_id));
  const items = [
    ...deadlineItems(deadlineRows),
    ...followupItems(followupRows),
    ...notificationItems(notificationRows, mutedIds),
  ].sort((a, b) => a.bucket - b.bucket || a.at - b.at);

  // Hiçbir kaynak veri vermediyse (boş ya da hepsi hata) yüzey çizilmez.
  if (items.length === 0) return null;

  const visible = items.slice(0, MAX_ROWS);
  const partial = deadlines.isError || followups.isError || notifications.isError;

  return (
    <Section title="Dikkat" hint={`${items.length}`}>
      <RowList>
        {visible.map((item) => {
          const Icon = item.icon;
          const body = (
            <>
              <Icon size={14} className={`mt-0.5 shrink-0 ${TONE_CLASS[item.tone]}`} aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-body text-primary">{item.title}</span>
                <span className="mt-0.5 block text-meta text-muted">{item.meta}</span>
              </span>
            </>
          );
          return item.href ? (
            <a key={item.key} href={item.href} className="flex items-start gap-2.5 py-2 hover:text-accent">
              {body}
            </a>
          ) : (
            <div key={item.key} className="flex items-start gap-2.5 py-2">
              {body}
            </div>
          );
        })}
      </RowList>
      {items.length > visible.length && (
        <p className="border-t border-subtle pt-2 text-meta text-muted">
          {items.length - visible.length} kayıt daha var.
        </p>
      )}
      {partial && (
        <p className="flex items-center gap-1.5 border-t border-subtle pt-2 text-meta text-muted">
          <AlertTriangle size={12} aria-hidden="true" />
          Bazı kaynaklara ulaşılamadı; liste eksik olabilir.
        </p>
      )}
    </Section>
  );
}
