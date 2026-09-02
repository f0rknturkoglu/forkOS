import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, ChevronDown, ChevronRight } from "lucide-react";
import { api, qs } from "@/core/api";
import { Chip, Empty, Metric, MetricStrip, PageFrame, PageHeader, Section, cx } from "@/core/ui";
import { useHashRoute } from "@/app/router";
import type { DayDetail } from "@/core/types";
import { formatTrDate, formatTrDateTime, localDateKey } from "@/lib/date";
import { typeLabel } from "@/core/entityRegistry";
import { ALERT_VERBS, VERB_LABELS, describe } from "@/core/verbs";

function shift(day: string, delta: number): string {
  const date = new Date(`${day}T12:00:00`); // ogle: yaz saati kaymasindan etkilenmez
  date.setDate(date.getDate() + delta);
  return localDateKey(date);
}

const today = () => localDateKey(new Date());

/**
 * Tek gunun sayfasi. Emek haritasindaki bir kareye tiklayinca buraya gelinir.
 *
 * Ust seritte o gun SAYILAN isler var; altta gunun tum hareketleri. Ikisi
 * ayri duruyor cunku worker'in kendi kayitlari (feed cekimi, hata) haritaya
 * girmiyor -- ama gunu incelerken gormek istersin.
 */
export function DayPage() {
  const [showSystem, setShowSystem] = useState(false);
  const { params } = useHashRoute();
  const day = params.get("d") ?? today();

  const { data, isLoading } = useQuery({
    queryKey: ["activity", "day", day],
    queryFn: () => api.get<DayDetail>(`/activity/day${qs({ day })}`),
  });

  const label = formatTrDate(day, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const isToday = day === today();
  const isFuture = day > today();

  // Kullanicinin eylemleri (emek haritasinda sayilanlar) ile worker'in
  // kayitlari ayri: gun sayfasi once "sen ne yaptin" sorusunu cevaplar.
  const mine = (data?.events ?? []).filter((event) => event.kind !== null);
  const system = (data?.events ?? []).filter((event) => event.kind === null);
  const grouped = Object.entries(
    system.reduce<Record<string, number>>((acc, event) => {
      acc[event.verb] = (acc[event.verb] ?? 0) + 1;
      return acc;
    }, {}),
  )
    .map(([verb, count]) => ({ verb, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Sistem"
        title={label}
        action={
          <nav className="flex items-center gap-1 text-meta">
            <a
              href={`#/day${qs({ d: shift(day, -1) })}`}
              className="flex items-center gap-1 rounded-control border border-subtle px-2.5 py-1.5 text-secondary transition hover:border-strong hover:text-primary"
            >
              <ArrowLeft size={13} /> önceki
            </a>
            {!isToday && (
              <a
                href={`#/day${qs({ d: today() })}`}
                className="rounded-control border border-subtle px-2.5 py-1.5 text-secondary transition hover:border-strong hover:text-primary"
              >
                bugün
              </a>
            )}
            <a
              href={`#/day${qs({ d: shift(day, 1) })}`}
              className={cx(
                "flex items-center gap-1 rounded-control border border-subtle px-2.5 py-1.5 transition",
                isFuture ? "pointer-events-none opacity-40" : "text-secondary hover:border-strong hover:text-primary",
              )}
              aria-disabled={isFuture}
            >
              sonraki <ArrowRight size={13} />
            </a>
          </nav>
        }
      />

      {isLoading ? (
        <p className="text-body text-muted">Yükleniyor…</p>
      ) : !data || data.events.length === 0 ? (
        <Empty variant="page" title="Bu günden kayıt yok">
          O gün forkOS kapalıydı ya da hiçbir şey işlenmedi.
        </Empty>
      ) : (
        <>
          {data.total > 0 && (
            <MetricStrip className="grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
              {Object.entries(data.kinds)
                .sort((a, b) => b[1] - a[1])
                .map(([kind, count]) => (
                  <Metric key={kind} label={data.labels[kind] ?? kind} value={count} />
                ))}
            </MetricStrip>
          )}

          <Section title="O gün ne yaptın" hint={`${mine.length} hareket`}>
            {mine.length === 0 ? (
              <Empty>Bu günde sayılan bir iş yok — sadece sistem kayıtları var.</Empty>
            ) : (
              <ul className="relative ml-1 border-l border-strong">
                {mine.map((event) => (
                  <li key={event.id} className="relative min-h-9 py-1.5 pl-5 text-body">
                    <span className="absolute -left-[5px] top-3" aria-hidden>
                      <span className="block h-2.5 w-2.5 rounded-full bg-accent ring-[3px] ring-surface" />
                    </span>
                    <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
                      <span className="numeral shrink-0 text-meta tabular-nums text-muted">
                        {formatTrDateTime(event.occurred_at, { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <span className="min-w-0 text-secondary">{describe(event.verb, event.payload)}</span>
                      {event.entity_type && <Chip>{typeLabel(event.entity_type)}</Chip>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {system.length > 0 && (
            <Section title="Sistem kayıtları" hint={`${system.length} kayıt`}>
              {/*
               * Worker'in kendi kayitlari (feed cekimi, sessizlesen kaynak,
               * hata) gunun asil hikayesini bogmasin diye kapali gelir ve
               * FIILE GORE toplanir -- 478 satir yerine bir avuc ozet.
               */}
              <button
                type="button"
                onClick={() => setShowSystem((v) => !v)}
                aria-expanded={showSystem}
                className="flex w-full items-center gap-1.5 text-left text-meta text-secondary transition hover:text-primary"
              >
                {showSystem ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                {showSystem ? "gizle" : "göster"}
                <span className="text-muted">
                  · {grouped.length} tür, {system.length} kayıt
                </span>
              </button>

              {showSystem && (
                <ul className="mt-3 divide-y divide-subtle border-t border-subtle">
                  {grouped.map((row) => (
                    <li key={row.verb} className="flex items-baseline justify-between gap-3 py-2">
                      <span
                        className={cx(
                          "min-w-0 truncate text-body",
                          ALERT_VERBS.has(row.verb) ? "text-warn" : "text-secondary",
                        )}
                      >
                        {VERB_LABELS[row.verb] ?? row.verb}
                      </span>
                      <span className="numeral shrink-0 text-meta tabular-nums text-muted">{row.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          )}
        </>
      )}
    </PageFrame>
  );
}
