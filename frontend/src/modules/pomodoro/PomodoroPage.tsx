import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button, Panel } from "@/core/ui";
import type { PomodoroSession, PomodoroStats, Todo } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";

function remaining(session: PomodoroSession | null | undefined, now: number) {
  if (!session) return 0;
  const elapsed = Math.floor((now - new Date(session.started_at).getTime()) / 1000);
  return Math.max(0, session.planned_min * 60 - elapsed);
}
function clock(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export function PomodoroPage() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  const initialContext = params.get("context") ?? "";
  const initialTitle = params.get("title") ?? "";
  const defaults = JSON.parse(localStorage.getItem("lifeos.pomodoroDefaults") ?? "{}");
  const [now, setNow] = useState(Date.now()); const [minutes, setMinutes] = useState(Number(defaults.focus) || 25);
  const [topic, setTopic] = useState(initialTitle); const [context, setContext] = useState(initialContext);
  const online = useOnline(); const invalidate = useInvalidate();
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id); }, []);
  const { data: active = null } = useQuery({ queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"), refetchInterval: 30_000 });
  const { data: stats } = useQuery({ queryKey: ["pomodoro-stats"],
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=week") });
  const { data: todos = [] } = useQuery({ queryKey: ["todos", "pomo-context"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=100") });
  const refresh = () => invalidate("pomodoro-active", "pomodoro-stats", "activity", "review-preview");
  const start = useMutation({ mutationFn: () => api.post("/pomodoro/start", {
    planned_min: minutes, topic: topic || undefined, context_entity_id: context || undefined,
  }), onSuccess: refresh });
  const stop = useMutation({ mutationFn: (interrupted: boolean) =>
    api.post(`/pomodoro/${active?.id}/stop`, { interrupted }), onSuccess: refresh });
  const left = remaining(active, now);
  useEffect(() => {
    if (active && left === 0 && !stop.isPending && online) stop.mutate(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, active?.id]);
  return <div className="space-y-4 p-6"><header><h1 className="text-xl font-semibold">Pomodoro</h1>
    <p className="text-xs text-neutral-500">Sayaç DB'deki started_at'a dayanir; sekme kapansa da devam eder.</p></header>
    <Panel className="mx-auto max-w-xl">
      {active ? <div className="space-y-5 text-center">
        <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">{active.topic || active.context_title || "Odak"}</div>
        <div className="font-mono text-7xl font-semibold tabular-nums">{clock(left)}</div>
        <div className="flex justify-center gap-2"><Button variant="primary" disabled={!online}
          onClick={() => stop.mutate(false)}>tamamla</Button><Button variant="danger" disabled={!online}
          onClick={() => stop.mutate(true)}>yarida kes</Button></div>
      </div> : <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-neutral-500">Dakika<input type="number" min={1} max={240} value={minutes}
          onChange={(event) => setMinutes(Number(event.target.value))}
          className="mt-1 w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100" /></label>
        <label className="text-xs text-neutral-500">Baglam<select value={context} onChange={(event) => setContext(event.target.value)}
          className="mt-1 w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100">
          <option value="">Bagimsiz</option>{initialContext && !todos.some(todo => todo.id === initialContext) && <option value={initialContext}>{initialTitle || "Çalışma konusu"}</option>}{todos.map((todo) => <option key={todo.id} value={todo.id}>{todo.title}</option>)}</select></label>
      </div><input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Konu (opsiyonel)"
        className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm" />
        <Button variant="primary" disabled={!online || start.isPending} onClick={() => start.mutate()}>odagi baslat</Button></div>}
    </Panel>
    <div className="grid grid-cols-3 gap-3">{[["Dakika", stats?.minutes ?? 0], ["Session", stats?.sessions ?? 0],
      ["Kesilen", stats?.interrupted ?? 0]].map(([label, value]) => <div key={label}
        className="rounded border border-neutral-800 p-3 text-center"><div className="text-2xl">{value}</div>
        <div className="text-xs text-neutral-500">{label}</div></div>)}</div>
  </div>;
}

export { clock, remaining };
