import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Maximize2, Pause, Play, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import {
  Button,
  Empty,
  Field,
  IconButton,
  Input,
  Metric,
  MetricStrip,
  PageFrame,
  RowList,
  Section,
  Select,
  cx,
  useToast,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import type { PomodoroSession, PomodoroStats } from "@/core/types";
import { useOnline } from "@/lib/hooks";
import { ContextChip, ContextPicker } from "./ContextPicker";
import { FocusMode } from "./FocusMode";
import { BREAK_MIN, FOCUS_MIN, clock, remaining } from "./time";

const KIND_LABELS: Record<string, string> = {
  focus: "odak",
  short_break: "mola",
  long_break: "uzun mola",
};

export function PomodoroPage() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  const [now, setNow] = useState(Date.now());
  const [focusMode, setFocusMode] = useState(false);
  const [minutes, setMinutes] = useState(FOCUS_MIN);
  const [topic, setTopic] = useState(params.get("title") ?? params.get("topic") ?? "");
  const [context, setContext] = useState(params.get("context") ?? "");
  const online = useOnline();
  const toast = useToast();

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const { data: active = null } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });
  const { data: stats } = useQuery({
    queryKey: ["pomodoro-stats"],
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=week"),
  });

  const refresh = () => invalidateAfter("pomodoro.write");
  const refreshTimeline = () => invalidateAfter("pomodoro.write");

  const start = useMutation({
    mutationFn: (kind: "focus" | "short_break") =>
      api.post("/pomodoro/start", {
        planned_min: kind === "focus" ? minutes : BREAK_MIN,
        kind,
        topic: kind === "focus" ? topic || undefined : undefined,
        context_entity_id: kind === "focus" ? context || undefined : undefined,
      }),
    onSuccess: refresh,
    onError: () => toast.push("Başlatılamadı — aktif bir seans olabilir.", { tone: "danger" }),
  });
  const stop = useMutation({
    mutationFn: (interrupted: boolean) => api.post(`/pomodoro/${active?.id}/stop`, { interrupted }),
    onSuccess: refreshTimeline,
  });
  const togglePause = useMutation({
    mutationFn: () => api.post(`/pomodoro/${active?.id}/${active?.paused_at ? "resume" : "pause"}`),
    onSuccess: refresh,
  });

  const left = remaining(active, now);
  const paused = Boolean(active?.paused_at);

  // Sure dolunca seansi kendisi kapatir -- ama duraklatilmisken degil.
  useEffect(() => {
    if (active && !paused && left === 0 && !stop.isPending && online) stop.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, active?.id, paused]);

  return (
    <>
      <PageFrame>
        <Workspace>
          <WorkspacePaneHeader
            eyebrow="Planlama"
            title="Pomodoro"
            hint={`Varsayılan ${FOCUS_MIN} dk odak · ${BREAK_MIN} dk mola`}
          />
          <WorkspaceScrollArea className="space-y-4 p-3">
            {active ? (
              <Section title={KIND_LABELS[active.kind] ?? active.kind} hint={paused ? "duraklatıldı" : "sürüyor"}>
                <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
                  <div>
                    <div
                      className={cx(
                        "numeral text-display-xl leading-none tabular-nums transition-colors",
                        paused ? "text-muted" : "text-primary",
                      )}
                    >
                      {clock(left)}
                    </div>
                    <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                      <span className="truncate">{active.topic || active.context_title || "Bağımsız"}</span>
                      <ContextChip type={active.context_type} />
                      <span>· {active.planned_min} dk</span>
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
                    <Button variant="primary" onClick={() => setFocusMode(true)}>
                      <Maximize2 size={14} /> odak modu
                    </Button>
                    <Button disabled={!online || togglePause.isPending} onClick={() => togglePause.mutate()}>
                      {paused ? (
                        <>
                          <Play size={14} /> devam et
                        </>
                      ) : (
                        <>
                          <Pause size={14} /> duraklat
                        </>
                      )}
                    </Button>
                    <Button disabled={!online} onClick={() => stop.mutate(false)}>
                      tamamla
                    </Button>
                    <Button variant="danger" disabled={!online} onClick={() => stop.mutate(true)}>
                      yarıda kes
                    </Button>
                  </div>
                </div>
              </Section>
            ) : (
              <Section title="Yeni blok">
                <div className="flex flex-wrap gap-2">
                  <Button variant="primary" disabled={!online || start.isPending} onClick={() => start.mutate("focus")}>
                    {minutes} dk odak başlat
                  </Button>
                  <Button disabled={!online || start.isPending} onClick={() => start.mutate("short_break")}>
                    {BREAK_MIN} dk mola
                  </Button>
                </div>

                <div className="mt-4 grid gap-3 border-t border-subtle pt-4 sm:grid-cols-3">
                  <Field label="Süre (dk)">
                    <Input
                      type="number"
                      value={String(minutes)}
                      onChange={(value) => setMinutes(Math.max(1, Math.min(240, Number(value) || FOCUS_MIN)))}
                      className="w-full"
                    />
                  </Field>
                  <Field label="Konu" className="sm:col-span-2">
                    <Input value={topic} onChange={setTopic} placeholder="Neye odaklanıyorsun?" className="w-full" />
                  </Field>
                  <div className="sm:col-span-3">
                    <ContextPicker value={context} onChange={setContext} />
                  </div>
                </div>
              </Section>
            )}

            <Section title="Bu hafta" bodyClassName="p-0">
              <MetricStrip className="grid-cols-3 rounded-none border-0 shadow-none">
                <Metric label="Dakika" value={stats?.minutes ?? 0} />
                <Metric label="Seans" value={stats?.sessions ?? 0} />
                <Metric label="Kesilen" value={stats?.interrupted ?? 0} />
              </MetricStrip>
            </Section>

            <SessionHistory onChange={refresh} onManualDone={refreshTimeline} />
          </WorkspaceScrollArea>
        </Workspace>
      </PageFrame>

      {focusMode && active && <FocusMode onClose={() => setFocusMode(false)} />}
    </>
  );
}

/** Gecmis seanslar: elle ekleme + silme. Sayac calismadan yapilan is de sayilir. */
function SessionHistory({ onChange, onManualDone }: { onChange: () => void; onManualDone: () => void }) {
  const [adding, setAdding] = useState(false);
  const online = useOnline();
  const toast = useToast();

  const { data: sessions = [] } = useQuery({
    queryKey: ["pomodoro-sessions"],
    queryFn: () => api.get<PomodoroSession[]>("/pomodoro/sessions?limit=20"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/pomodoro/${id}`),
    onSuccess: () => {
      onChange();
      toast.push("Seans silindi", { tone: "ok" });
    },
  });

  return (
    <Section
      title="Son seanslar"
      action={
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          className="flex items-center gap-1 text-meta text-accent hover:underline"
        >
          <Plus size={13} /> {adding ? "vazgeç" : "elle ekle"}
        </button>
      }
    >
      {adding && (
        <ManualForm
          onDone={() => {
            setAdding(false);
            onManualDone();
          }}
        />
      )}

      {sessions.length === 0 ? (
        <Empty>Henüz kayıtlı seans yok.</Empty>
      ) : (
        <RowList as="ul">
          {sessions.map((item) => (
            <li key={item.id} className="flex items-center gap-3 py-2">
              <span className={cx("h-2 w-2 shrink-0 rounded-full", item.interrupted ? "bg-warn" : "bg-ok")} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-body text-primary">
                  {item.topic || item.context_title || KIND_LABELS[item.kind] || "Odak"}
                  <ContextChip type={item.context_type} />
                </span>
                <span className="block text-meta text-muted">
                  {new Date(item.started_at).toLocaleString("tr-TR", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                  {" · "}
                  {item.actual_min ?? 0} dk
                  {item.interrupted && " · yarıda kesildi"}
                </span>
              </span>
              <IconButton
                title="Seansı sil"
                tone="danger"
                disabled={!online || remove.isPending}
                onClick={() => remove.mutate(item.id)}
              >
                <Trash2 size={14} />
              </IconButton>
            </li>
          ))}
        </RowList>
      )}
    </Section>
  );
}

function ManualForm({ onDone }: { onDone: () => void }) {
  // datetime-local yerel saat bekler; ISO'ya cevirirken tarayici saat dilimi kullanilir.
  const [when, setWhen] = useState(() => {
    const d = new Date(Date.now() - FOCUS_MIN * 60_000);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });
  const [minutes, setMinutes] = useState(FOCUS_MIN);
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const online = useOnline();
  const toast = useToast();

  const add = useMutation({
    mutationFn: () =>
      api.post("/pomodoro", {
        started_at: new Date(when).toISOString(),
        minutes,
        topic: topic || undefined,
        context_entity_id: context || undefined,
      }),
    onSuccess: () => {
      toast.push("Seans işlendi", { tone: "ok" });
      onDone();
    },
    onError: () => toast.push("İşlenemedi — tarih gelecekte olabilir.", { tone: "danger" }),
  });

  return (
    <form
      className="mb-3 grid gap-3 border-b border-subtle pb-4 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        add.mutate();
      }}
    >
      <Field label="Başlangıç">
        <Input type="datetime-local" value={when} onChange={setWhen} className="w-full" />
      </Field>
      <Field label="Süre (dk)">
        <Input
          type="number"
          value={String(minutes)}
          onChange={(value) => setMinutes(Math.max(1, Math.min(600, Number(value) || FOCUS_MIN)))}
          className="w-full"
        />
      </Field>
      <Field label="Konu">
        <Input value={topic} onChange={setTopic} placeholder="Ne üzerinde çalıştın?" className="w-full" />
      </Field>
      <ContextPicker value={context} onChange={setContext} />
      <div className="sm:col-span-2">
        <Button type="submit" variant="primary" disabled={!online || add.isPending}>
          Seansı işle
        </Button>
      </div>
    </form>
  );
}
