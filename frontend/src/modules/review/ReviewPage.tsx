import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel } from "@/core/ui";
import type { ReviewPreview } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";

function startOf(kind: "daily" | "weekly") {
  const day = new Date(); day.setHours(12, 0, 0, 0);
  if (kind === "weekly") day.setDate(day.getDate() - ((day.getDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}

function ReviewFlow({ kind }: { kind: "daily" | "weekly" }) {
  const [step, setStep] = useState(1); const [note, setNote] = useState("");
  const [decisions, setDecisions] = useState<Record<string, "carry" | "drop">>({});
  const [priorities, setPriorities] = useState(["", "", ""]); const online = useOnline();
  const invalidate = useInvalidate(); const period = useMemo(() => startOf(kind), [kind]);
  const { data, isLoading } = useQuery({ queryKey: ["review-preview", kind, period],
    queryFn: () => api.get<ReviewPreview>(`/reviews/preview${qs({ kind, period_start: period })}`) });
  const save = useMutation({ mutationFn: () => api.post("/reviews", {
    kind, period_start: period, note: note || undefined,
    decisions: { carry_over: Object.entries(decisions).filter(([, v]) => v === "carry").map(([id]) => id),
      drop: Object.entries(decisions).filter(([, v]) => v === "drop").map(([id]) => id),
      priorities: priorities.filter(Boolean) },
  }), onSuccess: () => { invalidate("review-preview", "reviews", "todos", "plan", "activity"); setStep(4); } });
  if (isLoading || !data) return <p className="p-6 text-sm text-neutral-500">Review hesaplaniyor...</p>;
  const stats = data.stats;
  return <div className="space-y-4 p-6"><header className="flex items-center justify-between"><div>
    <h1 className="text-xl font-semibold">{kind === "weekly" ? "Weekly" : "Daily"} Review</h1>
    <p className="text-xs text-neutral-500">{data.period_start} → {data.period_end}</p></div>
    <div className="flex gap-1">{[1, 2, 3].map((value) => <span key={value}
      className={`h-2 w-8 rounded ${step >= value ? "bg-sky-700" : "bg-neutral-800"}`} />)}</div></header>
    {step === 1 && <><div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {[ ["Tamamlanan", stats.todos.completed], ["Odak", `${stats.focus.minutes} dk`],
        ["Habit check", Object.values(stats.habits).reduce((a, b) => a + b, 0)],
        ["Capture", stats.capture.bookmarks] ].map(([label, value]) => <div key={String(label)}
          className="rounded border border-neutral-800 p-4"><div className="text-2xl font-semibold">{value}</div>
          <div className="text-xs text-neutral-500">{label}</div></div>)}</div>
      <Panel title="Odak dagilimi">{stats.topics.length === 0 ? <Empty>Bu donemde odak session'i yok.</Empty> :
        <ul className="space-y-2">{stats.topics.map((topic) => <li key={topic.topic} className="flex text-sm">
          <span>{topic.topic}</span><span className="ml-auto text-neutral-500">{topic.minutes} dk</span></li>)}</ul>}</Panel>
      <div className="flex justify-end"><Button variant="primary" onClick={() => setStep(2)}>kararlara gec →</Button></div></>}
    {step === 2 && <Panel title={`Bitmemis gorevler · ${data.unfinished_todos.length}`}
      action={data.unfinished_todos.length ? <Button onClick={() => setDecisions(Object.fromEntries(
        data.unfinished_todos.map((todo) => [todo.id, "carry"]))) }>hepsini devret</Button> : undefined}>
      {data.unfinished_todos.length === 0 ? <Empty>Acik gorev yok.</Empty> : <ul className="divide-y divide-neutral-800">
        {data.unfinished_todos.map((todo) => <li key={todo.id} className="flex flex-wrap items-center gap-2 py-3 text-sm">
          <span className="min-w-48 flex-1">{todo.title}</span><Badge>p{todo.priority}</Badge>
          <Button variant={decisions[todo.id] === "carry" ? "primary" : "ghost"}
            onClick={() => setDecisions((old) => ({ ...old, [todo.id]: "carry" }))}>devret</Button>
          <Button variant={decisions[todo.id] === "drop" ? "danger" : "ghost"}
            onClick={() => setDecisions((old) => ({ ...old, [todo.id]: "drop" }))}>birak</Button></li>)}</ul>}
      <div className="mt-4 flex justify-between"><Button onClick={() => setStep(1)}>← geri</Button>
        <Button variant="primary" onClick={() => setStep(3)}>onceliklere gec →</Button></div></Panel>}
    {step === 3 && <Panel title={kind === "weekly" ? "Gelecek haftanin 3 onceligi" : "Yarina aktar"}>
      <div className="space-y-2">{priorities.map((value, index) => <input key={index} value={value}
        onChange={(event) => setPriorities((old) => old.map((item, i) => i === index ? event.target.value : item))}
        placeholder={`${index + 1}. oncelik`} className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm" />)}</div>
      <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Not (opsiyonel)"
        className="mt-3 min-h-20 w-full rounded border border-neutral-700 bg-neutral-950 p-3 text-sm" />
      <div className="mt-3 flex justify-between"><Button onClick={() => setStep(2)}>← geri</Button><Button variant="primary"
        disabled={!online || save.isPending} onClick={() => save.mutate()}>review'u tamamla</Button></div></Panel>}
    {step === 4 && <Panel><div className="py-8 text-center"><div className="text-3xl">✓</div>
      <p className="mt-2 text-sm">Review donduruldu; kararlar plana islendi.</p></div></Panel>}
  </div>;
}

export function WeeklyReviewPage() { return <ReviewFlow kind="weekly" />; }
export function DailyReviewPage() { return <ReviewFlow kind="daily" />; }
