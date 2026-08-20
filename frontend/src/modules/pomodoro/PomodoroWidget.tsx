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
    className="text-xs text-neutral-500 hover:text-neutral-300">ac →</button>}>
    {active ? <div><div className="font-mono text-4xl tabular-nums">{clock(remaining(active, now))}</div>
      <p className="mt-1 truncate text-xs text-neutral-500">{active.topic || active.context_title || "Odak"}</p></div>
      : <button onClick={() => navigate("/pomodoro")} className="rounded border border-sky-800 px-3 py-2 text-sm text-sky-300">odak baslat</button>}
    <p className="mt-3 text-[11px] text-neutral-600">Bugun {stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} session</p>
  </Panel>;
}
