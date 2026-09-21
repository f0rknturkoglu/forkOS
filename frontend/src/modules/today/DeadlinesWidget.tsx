import { useQuery } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";
import { api } from "@/core/api";
import { typeLabel } from "@/core/entityRegistry";
import { RowList, Section } from "@/core/ui";
import type { Deadline } from "@/core/types";
import { dueTiming, entityHref, TodayRow } from "./TodayRow";

/**
 * Son tarihler (P2 §22): gerçek son tarihler listesi, tek soruya cevap.
 *
 * Kaynak `/deadlines`: modül sağlayıcılarından toplanan tarihli kayıtlar
 * (görev, kilometre taşı, ödeme, medya çıkışı, takvim, fırsat). Kart listenin
 * SONUNU tutar; her satır kaydın kendi rotasına gider.
 *
 * Kariyer son tarihleri (fırsat/mülakat) burada TEKRAR EDİLMEZ: sağ kolonda
 * hemen altındaki Kariyer kartı onları bağlamıyla gösterir. Aynı kaydı iki
 * kartta göstermek Home'u gürültülü yapardı.
 *
 * "Tümü" hedefi bilinçli olarak YOK: son tarihler altı modülden geliyor ve
 * hepsini tutan tek bir yüzey yok -- olmayan bir sayfaya bağlantı vermek
 * kullanıcıyı boşa tıklatırdı. Satır başına giden yer zaten kaydın kendisi.
 */

/** Kartta gösterilen en fazla satır. */
const MAX_ROWS = 5;

export function isCareerDeadline(row: Deadline): boolean {
  return row.type === "opportunity" || row.module === "opportunity";
}

export function DeadlinesWidget() {
  const { data } = useQuery({
    queryKey: ["deadlines"],
    queryFn: () => api.get<Deadline[]>("/deadlines"),
    retry: false,
  });

  const rows = (Array.isArray(data) ? data : [])
    .filter((row) => !isCareerDeadline(row))
    .sort((a, b) => a.due_at.localeCompare(b.due_at));
  if (rows.length === 0) return null;

  const visible = rows.slice(0, MAX_ROWS);
  const rest = rows.length - visible.length;

  return (
    <Section title="Son tarihler" hint={`${rows.length}`}>
      <RowList>
        {visible.map((row) => {
          const timing = dueTiming(row.due_at);
          return (
            <TodayRow
              key={row.entity_id}
              icon={CalendarClock}
              title={row.title}
              meta={`${timing.label} · ${typeLabel(row.type)}`}
              tone={timing.tone}
              href={entityHref(row.type, row.entity_id)}
            />
          );
        })}
      </RowList>
      {rest > 0 && <p className="border-t border-subtle pt-2 text-meta text-muted">{rest} kayıt daha var.</p>}
    </Section>
  );
}
