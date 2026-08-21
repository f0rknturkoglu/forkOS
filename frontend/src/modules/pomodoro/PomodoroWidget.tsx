import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { Panel } from "@/core/ui";
import type { PomodoroSession, PomodoroStats } from "@/core/types";
import { clock, remaining } from "./PomodoroPage";

export function PomodoroWidget() {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id); }, []);
  const { data: active } = useQuery({ queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active") });
  const { data: stats } = useQuery({ queryKey: ["pomodoro-stats", "today"],
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day") });
  return <Panel title="Pomodoro" action={<button onClick={() => navigate("/pomodoro")}
    className="text-meta text-muted hover:text-primary">aç →</button>}>
    {active ? <div><div className="font-mono text-4xl tabular-nums">{clock(remaining(active, now))}</div>
      <p className="mt-1 truncate text-meta text-muted">{active.topic || active.context_title || "Odak"}</p></div>
      : <button onClick={() => navigate("/pomodoro")} className="rounded border border-accent-border px-3 py-2 text-body text-accent">Odak başlat</button>}
    <p className="mt-3 text-meta text-muted">Bugün {stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} seans</p>
  </Panel>;
}
