import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  Input,
  Metric,
  MetricStrip,
  PageFrame,
  PageHeader,
  RowList,
  Section,
  Surface,
  Textarea,
} from "@/core/ui";
import type { ReviewPreview } from "@/core/types";
import { localDateKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { reviewMetricRows } from "./reviewMetrics";

function startOf(kind: "daily" | "weekly") {
  const day = new Date();
  day.setHours(12, 0, 0, 0);
  if (kind === "weekly") day.setDate(day.getDate() - ((day.getDay() + 6) % 7));
  return localDateKey(day);
}

function ReviewFlow({ kind }: { kind: "daily" | "weekly" }) {
  const [step, setStep] = useState(1);
  const [note, setNote] = useState("");
  const [decisions, setDecisions] = useState<Record<string, "carry" | "drop">>({});
  const [priorities, setPriorities] = useState(["", "", ""]);
  const online = useOnline();
  const period = useMemo(() => startOf(kind), [kind]);
  const { data, isLoading } = useQuery({
    queryKey: ["review-preview", kind, period],
    queryFn: () => api.get<ReviewPreview>(`/reviews/preview${qs({ kind, period_start: period })}`),
  });
  const save = useMutation({
    mutationFn: () =>
      api.post("/reviews", {
        kind,
        period_start: period,
        note: note || undefined,
        decisions: {
          carry_over: Object.entries(decisions)
            .filter(([, v]) => v === "carry")
            .map(([id]) => id),
          drop: Object.entries(decisions)
            .filter(([, v]) => v === "drop")
            .map(([id]) => id),
          priorities: priorities.filter(Boolean),
        },
      }),
    onSuccess: () => {
      invalidateAfter("review.write");
      setStep(4);
    },
  });
  if (isLoading || !data) return <p className="p-6 text-body text-muted">Değerlendirme hesaplanıyor…</p>;
  const stats = data.stats;
  return (
    <PageFrame className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <PageHeader eyebrow="Takip" title={`${kind === "weekly" ? "Haftalık" : "Günlük"} Değerlendirme`} />
        <div className="flex gap-1">
          {[1, 2, 3].map((value) => (
            <span key={value} className={`h-1 w-8 ${step >= value ? "bg-accent" : "bg-surface-sunken"}`} />
          ))}
        </div>
      </div>
      <p className="text-meta text-muted">
        {data.period_start} → {data.period_end}
      </p>
      {step === 1 && (
        <>
          <MetricStrip className="grid-cols-2 md:grid-cols-4">
            {reviewMetricRows(stats).map(([label, value]) => (
              <Metric key={label} label={label} value={value} />
            ))}
          </MetricStrip>
          <Section title="Odak dağılımı">
            {stats.topics.length === 0 ? (
              <Empty>Bu dönemde odak seansı yok.</Empty>
            ) : (
              <RowList as="ul">
                {stats.topics.map((topic) => (
                  <li key={topic.topic} className="flex py-2 text-body">
                    <span>{topic.topic}</span>
                    <span className="ml-auto text-muted">{topic.minutes} dk</span>
                  </li>
                ))}
              </RowList>
            )}
          </Section>
          <div className="flex justify-end">
            <Button variant="primary" onClick={() => setStep(2)}>
              kararlara geç →
            </Button>
          </div>
        </>
      )}
      {step === 2 && (
        <Section
          title={`Bitmemiş görevler · ${data.unfinished_todos.length}`}
          action={
            data.unfinished_todos.length ? (
              <Button
                onClick={() =>
                  setDecisions(Object.fromEntries(data.unfinished_todos.map((todo) => [todo.id, "carry"])))
                }
              >
                hepsini devret
              </Button>
            ) : undefined
          }
        >
          {data.unfinished_todos.length === 0 ? (
            <Empty>Açık görev yok.</Empty>
          ) : (
            <RowList as="ul">
              {data.unfinished_todos.map((todo) => (
                <li key={todo.id} className="flex flex-wrap items-center gap-2 py-3 text-body">
                  <span className="min-w-48 flex-1">{todo.title}</span>
                  <Chip>p{todo.priority}</Chip>
                  <Button
                    variant={decisions[todo.id] === "carry" ? "primary" : "ghost"}
                    onClick={() => setDecisions((old) => ({ ...old, [todo.id]: "carry" }))}
                  >
                    devret
                  </Button>
                  <Button
                    variant={decisions[todo.id] === "drop" ? "danger" : "ghost"}
                    onClick={() => setDecisions((old) => ({ ...old, [todo.id]: "drop" }))}
                  >
                    bırak
                  </Button>
                </li>
              ))}
            </RowList>
          )}
          <div className="mt-4 flex justify-between">
            <Button onClick={() => setStep(1)}>← geri</Button>
            <Button variant="primary" onClick={() => setStep(3)}>
              önceliklere geç →
            </Button>
          </div>
        </Section>
      )}
      {step === 3 && (
        <Surface className="p-4">
          <Section flat title={kind === "weekly" ? "Gelecek haftanın 3 önceliği" : "Yarına aktar"}>
            <div className="space-y-2">
              {priorities.map((value, index) => (
                <Input
                  key={index}
                  value={value}
                  onChange={(v) => setPriorities((old) => old.map((item, i) => (i === index ? v : item)))}
                  placeholder={`${index + 1}. oncelik`}
                  className="w-full"
                />
              ))}
            </div>
            <Textarea value={note} onChange={setNote} placeholder="Not (opsiyonel)" className="mt-3 min-h-20" />
            <div className="mt-3 flex justify-between">
              <Button onClick={() => setStep(2)}>← geri</Button>
              <Button variant="primary" disabled={!online || save.isPending} onClick={() => save.mutate()}>
                Değerlendirmeyi tamamla
              </Button>
            </div>
          </Section>
        </Surface>
      )}
      {step === 4 && (
        <Surface>
          <div className="py-8 text-center">
            <div className="text-3xl">✓</div>
            <p className="mt-2 text-body">Değerlendirme donduruldu; kararlar plana işlendi.</p>
          </div>
        </Surface>
      )}
    </PageFrame>
  );
}

export function WeeklyReviewPage() {
  return <ReviewFlow kind="weekly" />;
}
export function DailyReviewPage() {
  return <ReviewFlow kind="daily" />;
}
