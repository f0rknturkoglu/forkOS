import { ContextualHelp } from "@/core/ContextualHelp";
import { GoalStudio } from "./GoalStudio";
import { useHashRoute } from "@/app/router";
import { RelatedPanel } from "@/core/RelatedPanel";
import { useEffect, useState, type ComponentProps } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import {
  Button,
  Checkbox,
  Empty,
  Input as BaseInput,
  Field,
  Select,
  Textarea as BaseTextarea,
  PageFrame,
  Tabs,
  MetricStrip,
  Metric,
  useToast,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import type { components } from "@/generated/api-schema";

function Textarea(props: ComponentProps<typeof BaseTextarea>) {
  return (
    <Field label={props.ariaLabel ?? ""}>
      <BaseTextarea {...props} />
    </Field>
  );
}

function Input(props: ComponentProps<typeof BaseInput>) {
  return (
    <Field label={props.ariaLabel ?? ""}>
      <BaseInput
        step={props.type === "number" ? "any" : undefined}
        {...props}
        className={`w-full ${props.className ?? ""}`}
      />
    </Field>
  );
}

type S = components["schemas"];
type Overview = S["StrategyOverview"];
type Goal = S["GoalOut"];
type Objective = S["ObjectiveState"];
type KR = S["KeyResultOut"];
type Plan = S["PlanOut"];
const percent = (v: number | null | undefined) => (v == null ? "Ölçüm yok" : `%${v}`);
const pace: Record<string, string> = {
  ahead: "Önde",
  on_track: "Rotada",
  behind: "Geride",
  unknown: "Bilinmiyor",
  not_applicable: "Rota uygulanmıyor",
};
const confidence: Record<string, string> = { high: "Yüksek", medium: "Orta", low: "Düşük" };
const day = (date: string | null | undefined) => date?.slice(0, 10) ?? "";
const instant = (value: string) => (value ? new Date(value + "T00:00:00Z").toISOString() : null);

function useSave(after?: () => void) {
  const toast = useToast();
  return useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => {
      invalidateAfter("goal.write");
      after?.();
    },
    onError: (error: Error) => toast.push(error.message || "Kaydedilemedi", { tone: "danger" }),
  });
}

export function GoalsPage() {
  const { params } = useHashRoute();
  const requested = params.get("entity");
  const [studioOpen, setStudioOpen] = useState(false);
  const [studioGoalId, setStudioGoalId] = useState<string | null>(null);
  const [view, setView] = useState(params.get("view") ?? "overview");
  const [days, setDays] = useState<7 | 30 | 90>(30);
  const [selected, setSelected] = useState<string | null>(null);
  const read = useQuery({
    queryKey: ["strategy-overview", days],
    queryFn: () => api.get<Overview>(`/goals/strategy/overview?days=${days}`),
  });
  const history = useQuery({
    queryKey: ["strategy-history"],
    queryFn: () => api.get<S["StrategyHistory"]>("/goals/strategy/history"),
    enabled: view === "history",
  });
  const data = read.data;
  const objective = data?.objectives.find((o) => o.goal.id === selected);
  useEffect(() => {
    if (!requested || !data) return;
    const found = data.objectives.find(
      (o) =>
        o.goal.id === requested ||
        o.goal.milestones.some((m) => m.id === requested) ||
        o.key_results.some((k) => k.id === requested),
    );
    if (found) {
      setSelected(found.goal.id);
      setView("objectives");
    } else if (data.plans.some((p) => p.id === requested) || data.pillars.some((p) => p.id === requested))
      setView("plans");
  }, [requested, data?.objectives.length, data?.plans.length]);
  const detail = useQuery({
    queryKey: ["career-goal", selected],
    queryFn: () => api.get<Goal>(`/goals/${selected}`),
    enabled: Boolean(selected) && view === "objectives",
  });

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader eyebrow="Hedefler" title="Hedefler & Strateji">
          <Tabs
            value={view}
            onChange={setView}
            ariaLabel="Strateji görünümü"
            items={[
              { id: "overview", label: "Genel Bakış" },
              { id: "objectives", label: "Hedefler" },
              { id: "plans", label: "Plan" },
              { id: "history", label: "Geçmiş" },
            ]}
          />
        </WorkspacePaneHeader>
        <WorkspaceScrollArea className="min-w-0 stack-y-4 p-4">
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => {
                setStudioGoalId(null);
                setStudioOpen(true);
              }}
            >
              Hermes ile Hedef Hazırla
            </Button>
            {selected && (
              <Button
                onClick={() => {
                  setStudioGoalId(selected);
                  setStudioOpen(true);
                }}
              >
                Hermes ile Geliştir
              </Button>
            )}
          </div>
          {studioOpen && (
            <GoalStudio
              key={studioGoalId ?? "new"}
              goalId={studioGoalId}
              goals={data?.objectives.map((o) => o.goal) ?? []}
              onClose={() => setStudioOpen(false)}
            />
          )}
          {read.isPending && <p role="status">Strateji yükleniyor…</p>}
          {read.isError && (
            <div role="alert">
              Strateji yüklenemedi. <Button onClick={() => read.refetch()}>Yeniden dene</Button>
            </div>
          )}
          {data && (
            <>
              {data.warnings.map((r) => (
                <p key={r.code} role="status" className="text-meta text-warn">
                  {r.explanation}
                </p>
              ))}
              {view === "overview" && (
                <>
                  {!data.objectives.length && (
                    <Empty title="İlk hedefini tanımla">
                      Plan oluşturmak zorunlu değil.{" "}
                      <Button onClick={() => setView("objectives")}>Hedef oluştur</Button>
                    </Empty>
                  )}
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="flex-1 text-heading">Sonuç ve yürütme</h2>
                    <Select
                      value={String(days)}
                      onChange={(v) => setDays(Number(v) as 7 | 30 | 90)}
                      ariaLabel="Uyum penceresi"
                    >
                      <option value="7">Son 7 gün</option>
                      <option value="30">Son 30 gün</option>
                      <option value="90">Son 90 gün</option>
                    </Select>
                  </div>
                  <MetricStrip className="grid-cols-2 sm:grid-cols-3">
                    <Metric
                      label="Stratejik uyum"
                      value={percent(data.alignment.percent)}
                      hint={`${data.alignment.linked_count}/${data.alignment.eligible_count} anlamlı hareket`}
                    />
                    <Metric
                      label="Bağlanmamış hareket"
                      value={data.alignment.unaligned_count}
                      hint="Sonuç yüzdesini değiştirmez"
                    />
                    <Metric
                      label="Ölçülebilir hedef"
                      value={`${data.objectives.filter((o) => o.measurable_count > 0).length}/${data.objectives.length}`}
                      hint="Milestone ≠ stratejik sonuç"
                    />
                  </MetricStrip>
                  {data.alignment.warnings.map((r) => (
                    <p key={r.code} className="text-meta text-warn">
                      {r.explanation}
                    </p>
                  ))}
                  <p className="text-meta text-muted">
                    Uyum: anlamlı kullanıcı hareketleri ve açık hedef ilişkileri. Bir hareket birden fazla hedefe
                    bağlıysa dağılım eşit bölünür.
                  </p>
                  {data.plans
                    .filter((p) => p.status === "active")
                    .map((p) => {
                      const agg = data.plan_progress.find((a) => a.id === p.id);
                      return (
                        <div key={p.id} className="rounded-card border border-subtle p-3">
                          <h3 className="text-heading">
                            {p.title} · revizyon {p.revision}
                          </h3>
                          <p className="text-meta">
                            Sonuç: {percent(agg?.progress_percent)} · kapsam {agg?.measurable_objectives}/
                            {agg?.active_objectives} · kanıt {confidence[agg?.confidence ?? "low"]}
                          </p>
                          <p className="text-meta text-muted">
                            Genel yüzde için etkin hedeflerin en az %80'i tam ölçülebilir olmalı.
                          </p>
                          {p.summary && <p className="mt-2 text-body">{p.summary}</p>}
                        </div>
                      );
                    })}
                  {data.pillars.map((p) => {
                    const agg = data.pillar_progress.find((a) => a.id === p.id);
                    const allocation = data.alignment.pillars.find((a) => a.entity_id === p.id);
                    return (
                      <p key={p.id} className="text-body">
                        {p.title} · sonuç {percent(agg?.progress_percent)} · yürütme payı %
                        {allocation?.share_percent ?? 0}
                      </p>
                    );
                  })}
                  <h2 className="text-heading">Stratejik inceleme</h2>
                  {!data.findings.length && (
                    <p className="text-meta text-muted">Bu pencerede desteklenen bir risk saptanmadı.</p>
                  )}
                  {data.findings.map((f, i) => (
                    <div key={i} className="border-l-2 border-warn-border pl-3">
                      <p className="text-body">{f.observed_facts}</p>
                      <p className="text-meta text-muted">
                        {f.code} · {day(f.window_start)}–{day(f.window_end)}
                      </p>
                      <details className="text-meta">
                        <summary>Kanıt referansları</summary>
                        {[...f.entity_refs, ...f.evidence_refs].join(" · ")}
                      </details>
                    </div>
                  ))}
                  <div className="stack-divide-y divide-subtle">
                    {data.objectives.map((o) => (
                      <button
                        type="button"
                        key={o.goal.id}
                        onClick={() => {
                          setSelected(o.goal.id);
                          setView("objectives");
                        }}
                        className="flex w-full flex-wrap items-center gap-2 py-3 text-left"
                      >
                        <span className="min-w-0 flex-1 break-words">{o.goal.title}</span>
                        <span className="text-meta">
                          Sonuç {percent(o.strategic_progress_percent)} · adımlar{" "}
                          {percent(o.milestone_progress_percent)} · {pace[o.trajectory]}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}
              {view === "objectives" && (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={() => setSelected(null)}>Yeni hedef</Button>
                    {data.objectives.map((o) => (
                      <Button
                        key={o.goal.id}
                        variant={selected === o.goal.id ? "primary" : "ghost"}
                        onClick={() => setSelected(o.goal.id)}
                      >
                        {o.goal.title}
                      </Button>
                    ))}
                  </div>
                  <GoalEditor
                    key={selected ?? "new"}
                    goal={detail.data ?? objective?.goal}
                    data={data}
                    onSaved={setSelected}
                  />
                  {objective && (
                    <ContextualHelp
                      key={objective.goal.id}
                      context={{ kind: "goal", entity_id: objective.goal.id }}
                      label="Bu hedefte ilerliyor muyum?"
                    />
                  )}
                  {objective && (
                    <ObjectiveDetail key={objective.goal.id} objective={objective} providers={data.providers} />
                  )}
                  {data.objectives.some((o) => !o.goal.strategic_plan_id) && (
                    <p className="text-meta text-muted">
                      Plana atanmamış hedefler geçerlidir; mevcut kayıtlara otomatik anlam atanmaz.
                    </p>
                  )}
                </>
              )}
              {view === "plans" && <PlanEditor data={data} requested={requested} />}
            </>
          )}
          {view === "history" && (
            <>
              {history.isPending && <p role="status">Geçmiş yükleniyor…</p>}
              {history.isError && <p role="alert">Geçmiş yüklenemedi.</p>}
              {history.data && (
                <>
                  <p className="text-meta">
                    {history.data.comparison_reason}
                    {history.data.truncated ? " · Geçmiş liste sınırına ulaşıldı." : ""}
                  </p>
                  {history.data.comparable && (
                    <p>
                      Uyum değişimi: {history.data.alignment_delta ?? "Ölçüm yok"} puan · Hedef değişimleri:{" "}
                      {Object.entries(history.data.progress_deltas ?? {})
                        .map(
                          ([id, v]) => `${data?.objectives.find((o) => o.goal.id === id)?.goal.title ?? id}: ${v} puan`,
                        )
                        .join(" · ")}
                    </p>
                  )}
                  {!history.data.items.length && (
                    <Empty title="Henüz stratejik geçmiş yok">
                      Plan revizyonları ve kabul edilmiş Review kayıtları burada görünür.
                    </Empty>
                  )}
                  {history.data.items.map((item) => (
                    <details key={item.id} className="rounded-card border border-subtle p-3">
                      <summary>
                        {item.title} · {day(item.occurred_at)}
                      </summary>
                      <pre className="mt-2 whitespace-pre-wrap break-all text-meta">
                        {JSON.stringify(item.state, null, 2)}
                      </pre>
                    </details>
                  ))}
                </>
              )}
            </>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

function GoalEditor({ goal, data, onSaved }: { goal?: Goal; data: Overview; onSaved: (id: string) => void }) {
  const [title, setTitle] = useState(goal?.title ?? "");
  const [description, setDescription] = useState(goal?.description ?? "");
  const [status, setStatus] = useState(goal?.status ?? "active");
  const [horizon, setHorizon] = useState(goal?.horizon ?? "quarter");
  const [date, setDate] = useState(day(goal?.target_at));
  const [plan, setPlan] = useState(goal?.strategic_plan_id ?? "");
  const [pillar, setPillar] = useState(goal?.pillar_id ?? "");
  const [parent, setParent] = useState(goal?.parent_goal_id ?? "");
  const [priority, setPriority] = useState(String(goal?.priority ?? 2));
  const [weight, setWeight] = useState(String(goal?.weight ?? 1));
  const save = useSave();
  return (
    <form
      className="stack-y-3 rounded-card border border-subtle p-3"
      onSubmit={(e) => {
        e.preventDefault();
        const body = {
          title,
          description: description || null,
          status,
          horizon,
          target_at: instant(date),
          strategic_plan_id: plan || null,
          pillar_id: pillar || null,
          parent_goal_id: parent || null,
          priority: Number(priority),
          weight,
        };
        save.mutate(async () => {
          const result = goal ? await api.patch<Goal>(`/goals/${goal.id}`, body) : await api.post<Goal>("/goals", body);
          onSaved(result.id);
        });
      }}
    >
      <h2 className="text-heading">{goal ? "Hedefi düzenle" : "Yeni hedef"}</h2>
      <Input value={title} onChange={setTitle} ariaLabel="Hedef başlığı" placeholder="Nereye ulaşmak istiyorum?" />
      <Textarea value={description} onChange={setDescription} ariaLabel="Hedef açıklaması" />
      <details>
        <summary className="text-meta">Plan, öncelik ve tarih</summary>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Select value={status} onChange={(v) => setStatus(v as typeof status)} ariaLabel="Hedef durumu">
            <option value="active">Aktif</option>
            <option value="paused">Duraklatıldı</option>
            <option value="completed">Tamamlandı</option>
            <option value="retired">Emekli</option>
          </Select>
          <Select value={horizon} onChange={(v) => setHorizon(v as typeof horizon)} ariaLabel="Hedef ufku">
            <option value="short_term">Kısa vade</option>
            <option value="quarter">Çeyrek</option>
            <option value="year">Yıl</option>
            <option value="long_term">Uzun vade</option>
          </Select>
          <Input type="date" value={date} onChange={setDate} ariaLabel="Hedef tarihi" />
          <Select value={priority} onChange={setPriority} ariaLabel="Hedef önceliği">
            <option value="1">Düşük öncelik</option>
            <option value="2">Normal öncelik</option>
            <option value="3">Yüksek öncelik</option>
          </Select>
          <Select
            value={plan}
            onChange={(v) => {
              setPlan(v);
              setPillar("");
            }}
            ariaLabel="Stratejik plan"
          >
            <option value="">Plana atanmamış</option>
            {data.plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </Select>
          <Select value={pillar} onChange={setPillar} ariaLabel="Stratejik alan">
            <option value="">Alana atanmamış</option>
            {data.pillars
              .filter((p) => p.plan_id === plan)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
          </Select>
          <Select value={parent} onChange={setParent} ariaLabel="Üst hedef">
            <option value="">Üst hedef yok</option>
            {data.objectives
              .filter((o) => o.goal.id !== goal?.id)
              .map((o) => (
                <option key={o.goal.id} value={o.goal.id}>
                  {o.goal.title}
                </option>
              ))}
          </Select>
          <Input type="number" value={weight} onChange={setWeight} ariaLabel="Hedef ağırlığı" />
        </div>
      </details>
      <Button type="submit" disabled={!title.trim() || save.isPending}>
        {goal ? "Hedefi kaydet" : "Hedef oluştur"}
      </Button>
    </form>
  );
}

function ObjectiveDetail({ objective: o, providers }: { objective: Objective; providers: Overview["providers"] }) {
  const [milestone, setMilestone] = useState("");
  const [editKR, setEditKR] = useState<KR | null>(null);
  const [showKR, setShowKR] = useState(false);
  const save = useSave();
  return (
    <div className="stack-y-3">
      <MetricStrip className="grid-cols-2 sm:grid-cols-4">
        <Metric
          label="Stratejik sonuç"
          value={percent(o.strategic_progress_percent)}
          hint={`${o.measurable_count}/${o.active_kr_count} ölçülebilir KR`}
        />
        <Metric
          label="Milestone tamamlanması"
          value={percent(o.milestone_progress_percent)}
          hint="Sonuç ilerlemesi değildir"
        />
        <Metric label="Rota" value={pace[o.trajectory]} hint={`Beklenen ${percent(o.expected_percent)}`} />
        <Metric label="Kanıt kalitesi" value={confidence[o.confidence]} hint="Kullanıcı/model puanı değil" />
      </MetricStrip>
      {o.reasons.map((r, i) => (
        <p key={i} className="text-meta text-muted">
          {r.code}: {r.explanation}
        </p>
      ))}
      <h3 className="text-heading">Ölçülebilir sonuçlar (Key Results)</h3>
      <Button
        onClick={() => {
          setEditKR(null);
          setShowKR(true);
        }}
      >
        KR ekle
      </Button>
      {o.key_results.map((k) => (
        <div key={k.id} className="rounded-card border border-subtle p-3">
          <div className="flex flex-wrap gap-2">
            <h4 className="min-w-0 flex-1 break-words text-body">{k.title}</h4>
            <Button
              size="sm"
              onClick={() => {
                setEditKR(k);
                setShowKR(true);
              }}
            >
              KR düzenle
            </Button>
          </div>
          <p className="text-meta">
            {k.measurement.current_value ?? "Ölçüm yok"} / {k.target_value} {k.unit} ·{" "}
            {percent(k.measurement.progress_percent)} · {pace[k.measurement.trajectory]} · ağırlık {k.weight}
          </p>
          <p className="text-meta text-muted">
            {providers.find((p) => p.key === k.source_key)?.label} · Kanıt: {confidence[k.measurement.confidence]}
          </p>
          {(k.measurement.reasons ?? []).map((r) => (
            <p key={r.code} className="text-meta text-muted">
              {r.explanation}
            </p>
          ))}
          <details className="text-meta">
            <summary>Ölçüm kanıtları</summary>
            {(k.measurement.evidence_refs ?? []).join(" · ") || "Kanonik kayıt sayısı sıfır / ölçüm yok"}
          </details>
        </div>
      ))}
      {o.key_results.map((k) => (
        <details key={k.id}>
          <summary className="text-meta">{k.title} bağlantıları</summary>
          <RelatedPanel entityId={k.id} />
        </details>
      ))}
      {showKR && (
        <KREditor
          key={editKR?.id ?? "new"}
          goalId={o.goal.id}
          kr={editKR}
          providers={providers}
          onSaved={() => setShowKR(false)}
        />
      )}
      <h3 className="text-heading">Yürütme ve adımlar</h3>
      {o.goal.milestones.map((m) => (
        <details key={m.id}>
          <summary className="text-meta">{m.title} bağlantıları</summary>
          <RelatedPanel entityId={m.id} relation="advances_goal_milestone" incoming />
        </details>
      ))}
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(() =>
            api.post(`/goals/${o.goal.id}/milestones`, { title: milestone }).then(() => setMilestone("")),
          );
        }}
      >
        <Input value={milestone} onChange={setMilestone} ariaLabel="Yeni hedef adımı" />
        <Button type="submit" disabled={!milestone.trim()}>
          Adım ekle
        </Button>
      </form>
      {o.goal.milestones.map((m) => (
        <Checkbox
          key={m.id}
          label={m.title}
          checked={Boolean(m.completed_at)}
          onChange={(completed) => save.mutate(() => api.patch(`/goal-milestones/${m.id}`, { completed }))}
        />
      ))}
      <RelatedPanel entityId={o.goal.id} title="Hedefi destekleyen kayıtlar" relation="advances_goal" incoming />
      <details className="text-meta">
        <summary>Yakın dönem kanıtları</summary>
        {o.evidence_refs.join(" · ")}
      </details>
    </div>
  );
}

function KREditor({
  goalId,
  kr,
  providers,
  onSaved,
}: {
  goalId: string;
  kr: KR | null;
  providers: Overview["providers"];
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(kr?.title ?? "");
  const [baseline, setBaseline] = useState(String(kr?.baseline_value ?? 0));
  const [target, setTarget] = useState(String(kr?.target_value ?? 100));
  const [value, setValue] = useState(kr?.manual_value == null ? "" : String(kr.manual_value));
  const [unit, setUnit] = useState(kr?.unit ?? "adet");
  const [weight, setWeight] = useState(String(kr?.weight ?? 1));
  const [source, setSource] = useState(kr?.source_key ?? "manual");
  const [linked, setLinked] = useState(kr?.source_config?.linked_entity_id ?? "");
  const [since, setSince] = useState(day(kr?.source_config?.since));
  const [direction, setDirection] = useState(kr?.direction ?? "increase");
  const [model, setModel] = useState(kr?.trajectory_model ?? "none");
  const [start, setStart] = useState(day(kr?.start_at));
  const [end, setEnd] = useState(day(kr?.target_at));
  const [status, setStatus] = useState(kr?.status ?? "active");
  const save = useSave(onSaved);
  return (
    <form
      className="stack-y-3 rounded-card border border-subtle p-3"
      onSubmit={(e) => {
        e.preventDefault();
        const body = {
          title,
          description: kr?.description ?? null,
          status,
          baseline_value: baseline,
          target_value: target,
          manual_value: source === "manual" && value ? value : null,
          weight,
          unit,
          source_key: source,
          source_config:
            source === "linked_completion"
              ? { linked_entity_id: linked }
              : source.startsWith("applications_") && since
                ? { since: instant(since) }
                : {},
          direction,
          trajectory_model: model,
          start_at: instant(start),
          target_at: instant(end),
          position: kr?.position ?? 0,
        };
        save.mutate(() =>
          kr ? api.put(`/goals/${goalId}/key-results/${kr.id}`, body) : api.post(`/goals/${goalId}/key-results`, body),
        );
      }}
    >
      <h3 className="text-heading">{kr ? "KR düzenle" : "Yeni KR"}</h3>
      <Input value={title} onChange={setTitle} ariaLabel="KR başlığı" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input type="number" value={baseline} onChange={setBaseline} ariaLabel="Başlangıç değeri" />
        <Input type="number" value={target} onChange={setTarget} ariaLabel="Hedef değeri" />
        <Input value={unit} onChange={setUnit} ariaLabel="Birim" />
        <Input type="number" value={weight} onChange={setWeight} ariaLabel="KR ağırlığı" />
        <Select value={direction} onChange={(v) => setDirection(v as typeof direction)} ariaLabel="Ölçüm yönü">
          <option value="increase">Artış</option>
          <option value="decrease">Azalış</option>
        </Select>
        <Select value={source} onChange={(v) => setSource(v as typeof source)} ariaLabel="Metrik kaynağı">
          {providers.map((p) => (
            <option key={p.key} value={p.key}>
              {p.label}
            </option>
          ))}
        </Select>
      </div>
      <p className="text-meta text-muted">{providers.find((p) => p.key === source)?.description}</p>
      {source === "manual" && <Input type="number" value={value} onChange={setValue} ariaLabel="Güncel ölçüm değeri" />}
      {source === "linked_completion" && <Input value={linked} onChange={setLinked} ariaLabel="Ölçülen kayıt UUID" />}
      {source.startsWith("applications_") && (
        <Input type="date" value={since} onChange={setSince} ariaLabel="Başvuru kohortu başlangıcı" />
      )}
      <details>
        <summary className="text-meta">Rota ve durum</summary>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          <Select value={model} onChange={(v) => setModel(v as typeof model)} ariaLabel="Rota modeli">
            <option value="none">Rota uygulanmıyor</option>
            <option value="linear">Doğrusal</option>
            <option value="deadline">Son tarihte eşik</option>
          </Select>
          <Select value={status} onChange={(v) => setStatus(v as typeof status)} ariaLabel="KR durumu">
            <option value="active">Aktif</option>
            <option value="paused">Duraklatıldı</option>
            <option value="completed">Tamamlandı</option>
            <option value="retired">Emekli</option>
          </Select>
          <Input type="date" value={start} onChange={setStart} ariaLabel="KR başlangıç tarihi" />
          <Input type="date" value={end} onChange={setEnd} ariaLabel="KR hedef tarihi" />
        </div>
      </details>
      <Button type="submit" disabled={!title.trim() || save.isPending}>
        KR kaydet
      </Button>{" "}
      <Button variant="ghost" onClick={onSaved}>
        Vazgeç
      </Button>
    </form>
  );
}

function PlanEditor({ data, requested }: { data: Overview; requested: string | null }) {
  const [id, setId] = useState(
    data.plans.find((p) => p.id === requested)?.id ?? data.pillars.find((p) => p.id === requested)?.plan_id ?? "",
  );
  const plan = data.plans.find((p) => p.id === id);
  return (
    <div className="stack-y-3">
      <Select value={id} onChange={setId} ariaLabel="Düzenlenecek plan">
        <option value="">Yeni stratejik plan</option>
        {data.plans.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title} · r{p.revision}
          </option>
        ))}
      </Select>
      <PlanForm key={id || "new"} plan={plan} onSaved={setId} />
      {plan && <Pillars plan={plan} data={data} />}
    </div>
  );
}
function PlanForm({ plan, onSaved }: { plan?: Plan; onSaved: (id: string) => void }) {
  const [title, setTitle] = useState(plan?.title ?? "");
  const [summary, setSummary] = useState(plan?.summary ?? "");
  const [start, setStart] = useState(day(plan?.start_at));
  const [end, setEnd] = useState(day(plan?.end_at));
  const [path, setPath] = useState(plan?.narrative_path ?? "");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState(plan?.status ?? "active");
  const save = useSave();
  return (
    <form
      className="stack-y-3 rounded-card border border-subtle p-3"
      onSubmit={(e) => {
        e.preventDefault();
        const body = {
          title,
          summary: summary || null,
          start_at: instant(start),
          end_at: instant(end),
          status,
          narrative_path: path || null,
          change_reason: reason || null,
        };
        save.mutate(async () => {
          const result = plan
            ? await api.put<Plan>(`/goals/strategy/plans/${plan.id}`, body)
            : await api.post<Plan>("/goals/strategy/plans", body);
          onSaved(result.id);
        });
      }}
    >
      <h2 className="text-heading">{plan ? "Planı düzenle" : "Yeni stratejik plan"}</h2>
      <Input value={title} onChange={setTitle} ariaLabel="Plan başlığı" />
      <Textarea value={summary} onChange={setSummary} ariaLabel="Plan özeti" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input type="date" value={start} onChange={setStart} ariaLabel="Plan başlangıcı" />
        <Input type="date" value={end} onChange={setEnd} ariaLabel="Plan bitişi" />
      </div>
      <Input
        value={path}
        onChange={setPath}
        ariaLabel="Vault anlatı yolu"
        placeholder="Göreli Markdown yolu (isteğe bağlı)"
      />
      <Input value={reason} onChange={setReason} ariaLabel="Revizyon nedeni" />
      <Select value={status} onChange={(v) => setStatus(v as typeof status)} ariaLabel="Plan durumu">
        <option value="active">Aktif</option>
        <option value="paused">Duraklatıldı</option>
        <option value="archived">Arşiv</option>
        <option value="superseded">Yerine yeni plan geçti</option>
      </Select>
      <p className="text-meta text-muted">
        Her kaydetme incelenebilir bir revizyon oluşturur. Vault notu otomatik değiştirilmez.
      </p>
      <Button type="submit" disabled={!title.trim() || !start || !end || save.isPending}>
        Planı kaydet
      </Button>
    </form>
  );
}
function Pillars({ plan, data }: { plan: Plan; data: Overview }) {
  const [id, setId] = useState("");
  const [title, setTitle] = useState("");
  const [weight, setWeight] = useState("1");
  const save = useSave(() => {
    setTitle("");
    setId("");
  });
  return (
    <div className="stack-y-3">
      <RelatedPanel entityId={plan.id} />
      {data.pillars
        .filter((p) => p.plan_id === plan.id)
        .map((p) => (
          <details key={p.id}>
            <summary className="text-meta">{p.title} bağlantıları</summary>
            <RelatedPanel entityId={p.id} />
          </details>
        ))}
      <h3 className="text-heading">Stratejik alanlar</h3>
      {data.pillars
        .filter((p) => p.plan_id === plan.id)
        .map((p) => (
          <Button
            key={p.id}
            variant="ghost"
            onClick={() => {
              setId(p.id);
              setTitle(p.title);
              setWeight(String(p.weight));
            }}
          >
            {p.title}
          </Button>
        ))}
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(() =>
            id
              ? api.put(`/goals/strategy/plans/${plan.id}/pillars/${id}`, { title, weight })
              : api.post(`/goals/strategy/plans/${plan.id}/pillars`, { title, weight }),
          );
        }}
      >
        <Input value={title} onChange={setTitle} ariaLabel="Stratejik alan adı" placeholder="Kendi alanını tanımla" />
        <Input type="number" value={weight} onChange={setWeight} ariaLabel="Alan ağırlığı" />
        <Button type="submit" disabled={!title.trim()}>
          {id ? "Alanı kaydet" : "Alan ekle"}
        </Button>
      </form>
    </div>
  );
}
