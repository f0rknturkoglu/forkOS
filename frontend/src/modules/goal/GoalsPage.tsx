import { GoalLivingWorkspace } from "./GoalLivingWorkspace";
import { GoalWorkArea } from "./GoalWorkArea";
import { ArrowLeft, Pencil, Plus } from "lucide-react";
import { appLocalToUtc, formatAppDate, localDateKey } from "@/lib/date";
import { GoalStudio } from "./GoalStudio";
import { navigate, useHashRoute } from "@/app/router";
import { RelatedPanel } from "@/core/RelatedPanel";
import { useEffect, useState, useCallback, type ComponentProps } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import {
  Button,
  Checkbox,
  Disclosure,
  Empty,
  Input as BaseInput,
  Field,
  Select,
  Textarea as BaseTextarea,
  PageFrame,
  Tabs,
  Modal,
  MetricStrip,
  Metric,
  useToast,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
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
const day = (date: string | null | undefined) => (date ? localDateKey(new Date(date)) : "");
const instant = (value: string) => (value ? appLocalToUtc(value, 0, 0) : null);

function useSave(after?: () => void) {
  const toast = useToast();
  const online = useOnline();
  const mutation = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => {
      invalidateAfter("goal.write");
      after?.();
    },
    onError: (error: Error) => toast.push(error.message || "Kaydedilemedi", { tone: "danger" }),
  });
  return { ...mutation, isPending: mutation.isPending || !online };
}

export function GoalsPage() {
  const online = useOnline();
  const queryClient = useQueryClient();
  const { params } = useHashRoute();
  const requested = params.get("entity");
  const [selected, setSelected] = useState<string | null>(requested);
  const [createOpen, setCreateOpen] = useState(false);
  const [composer, setComposer] = useState("");
  const [longTerm, setLongTerm] = useState(false);
  const [initialRequest, setInitialRequest] = useState("");
  const [scopeCounts, setScopeCounts] = useState<{ completed: number; total: number } | null>(null);
  const updateProgress = useCallback((pct: number | null, counts: { completed: number; total: number }) => {
    setRoadmapPercent(pct);
    setScopeCounts(counts);
  }, []);
  const [roadmapPercent, setRoadmapPercent] = useState<number | null | undefined>(undefined);
  const [manual, setManual] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(["plans", "history", "overview"].includes(params.get("view") ?? ""));
  const [view, setView] = useState(params.get("view") ?? "plans");
  const read = useQuery({
    queryKey: ["strategy-overview", 30],
    queryFn: () => api.get<Overview>("/goals/strategy/overview?days=30"),
  });
  const history = useQuery({
    queryKey: ["strategy-history"],
    queryFn: () => api.get<S["StrategyHistory"]>("/goals/strategy/history"),
    enabled: advancedOpen && view === "history",
  });
  const data = read.data;
  const objective = data?.objectives.find((o) => o.goal.id === selected);
  const detail = useQuery({
    queryKey: ["career-goal", selected],
    queryFn: () => api.get<Goal>(`/goals/${selected}`),
    enabled: Boolean(selected) && !objective,
  });
  const owner = useQuery({
    queryKey: ["goal-node-owner", requested],
    queryFn: () => api.get<{ goal_id: string }>(`/goals/roadmap-nodes/${requested}`),
    enabled: Boolean(requested) && detail.isError && !objective,
    retry: false,
  });
  useEffect(() => {
    if (owner.data) setSelected(owner.data.goal_id);
  }, [owner.data]);
  const goal = objective?.goal ?? detail.data;
  useEffect(() => {
    setRoadmapPercent(undefined);
    setScopeCounts(null);
  }, [selected]);
  useEffect(() => {
    setCreateOpen(false);
  }, [requested]);
  useEffect(() => {
    if (!requested || !data) return;
    const found = data.objectives.find(
      (o) =>
        o.goal.id === requested ||
        o.goal.milestones.some((m) => m.id === requested) ||
        o.key_results.some((k) => k.id === requested),
    );
    if (found) setSelected(found.goal.id);
    else if (data.plans.some((p) => p.id === requested) || data.pillars.some((p) => p.id === requested)) {
      setAdvancedOpen(true);
      setView("plans");
    }
  }, [requested, data]);
  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          title="Hedefler"
          hint="Bir hedef seç, sıradaki adımını tamamla."
          action={
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => setAdvancedOpen(true)}>
                Geçmiş ve gelişmiş ayarlar
              </Button>
              <span data-onboarding="goal-create">
                <Button variant="primary" disabled={!online} onClick={() => setCreateOpen(true)}>
                  <Plus size={14} /> Yeni hedef
                </Button>
              </span>
            </div>
          }
        />
        <WorkspaceScrollArea className="p-4">
          <div className="mx-auto max-w-4xl stack-y-5">
            {read.isPending && <p role="status">Hedefler yükleniyor…</p>}
            {read.isError && (
              <div role="alert">
                Hedefler alınamadı.{" "}
                <Button
                  onClick={async () => {
                    await queryClient.refetchQueries({ queryKey: ["entity-types"] });
                    await read.refetch();
                  }}
                >
                  Yeniden dene
                </Button>
              </div>
            )}
            {data && (
              <>
                {!selected ? (
                  <div className="stack-y-5">
                    <section
                      className="rounded-card border border-subtle bg-surface p-5 stack-y-3"
                      aria-label="Hedefini anlat"
                    >
                      <h2 className="text-title font-semibold">Neyi başarmak istiyorsun?</h2>
                      <p className="text-body text-secondary">
                        Hedefini ve ayırabileceğin zamanı anlat. Hermes yapılabilir bir yol haritası, görevler ve
                        öğrenme planı hazırlasın.
                      </p>
                      <Textarea
                        ariaLabel="Yeni hedef isteği"
                        value={composer}
                        onChange={setComposer}
                        rows={4}
                        placeholder="Örneğin: YDS’den en az 55 almak istiyorum. Günde iki saat çalışabilirim."
                      />
                      <div className="flex flex-wrap items-center gap-3">
                        <Checkbox label="Uzun vadeli" checked={longTerm} onChange={setLongTerm} />
                        <Button
                          variant="primary"
                          disabled={!online || !composer.trim()}
                          onClick={() => {
                            setInitialRequest(composer.trim());
                            setCreateOpen(true);
                            setManual(false);
                          }}
                        >
                          Hedef planımı hazırla
                        </Button>
                        <Button
                          variant="ghost"
                          disabled={!online}
                          onClick={() => {
                            setManual(true);
                            setCreateOpen(true);
                          }}
                        >
                          Kendim oluştur
                        </Button>
                      </div>
                    </section>
                    {data.objectives.length ? (
                      <div className="grid gap-3 sm:grid-cols-2">
                        {data.objectives
                          .filter((o) => !o.goal.parent_goal_id)
                          .map((o) => (
                            <button
                              key={o.goal.id}
                              type="button"
                              onClick={() => {
                                setSelected(o.goal.id);
                                navigate(`/goals?entity=${encodeURIComponent(o.goal.id)}`);
                              }}
                              className="rounded-card border border-subtle bg-surface p-4 text-left transition hover:border-strong stack-y-3"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <h2 className="text-heading">{o.goal.title}</h2>
                                <span className="font-sans text-title font-bold tabular-nums">
                                  {(o.roadmap_progress_percent !== undefined
                                    ? o.roadmap_progress_percent
                                    : o.work?.progress_percent) == null
                                    ? "—"
                                    : `%${o.roadmap_progress_percent !== undefined ? o.roadmap_progress_percent : o.work?.progress_percent}`}
                                </span>
                              </div>
                              <WorkProgress
                                work={
                                  o.roadmap_progress_percent !== undefined
                                    ? { ...o.work, progress_percent: o.roadmap_progress_percent }
                                    : o.work
                                }
                              />
                              <p className="text-meta text-muted">
                                {(o.roadmap_scope_count ?? o.work?.total_count)
                                  ? `${o.roadmap_completed_scope_count ?? o.work?.completed_count}/${o.roadmap_scope_count ?? o.work?.total_count} ana adım tamamlandı`
                                  : "İlk adımını ekle"}
                                {o.goal.target_at
                                  ? ` · ${formatAppDate(o.goal.target_at, { day: "numeric", month: "long", year: "numeric" })}`
                                  : ""}
                              </p>
                            </button>
                          ))}
                      </div>
                    ) : (
                      <Empty title="İlk hedefini oluştur">
                        <span>Ne başarmak istediğini Hermes’e anlat; birlikte yapılabilir adımlara ayırın.</span>
                        <Button variant="primary" disabled={!online} onClick={() => setCreateOpen(true)}>
                          Hedef oluştur
                        </Button>
                      </Empty>
                    )}
                  </div>
                ) : (
                  <>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setSelected(null);
                        navigate("/goals");
                      }}
                    >
                      <ArrowLeft size={14} /> Tüm hedefler
                    </Button>
                    {goal ? (
                      <div className="rounded-card border border-subtle p-4 stack-y-3">
                        <div className="flex flex-wrap items-start gap-3">
                          <div className="min-w-0 flex-1">
                            <h2 className="text-title font-semibold break-words">{goal.title}</h2>
                            {goal.target_at && (
                              <p className="mt-1 text-meta text-secondary">
                                Hedef tarihi:{" "}
                                {formatAppDate(goal.target_at, { day: "numeric", month: "long", year: "numeric" })}
                              </p>
                            )}
                          </div>
                          <Button size="sm" disabled={!online} onClick={() => setEditOpen(true)}>
                            <Pencil size={13} /> Düzenle
                          </Button>
                        </div>
                        {goal.description && (
                          <Disclosure summary="Çalışma planını oku">
                            <p className="whitespace-pre-wrap text-body text-secondary">{goal.description}</p>
                          </Disclosure>
                        )}
                        <div className="flex items-baseline justify-between gap-3">
                          <span className="text-body text-secondary">Çalışma ilerlemesi</span>
                          <strong className="font-sans text-display font-bold tabular-nums">
                            {roadmapPercent === undefined
                              ? objective?.work?.progress_percent == null
                                ? "—"
                                : `%${objective.work.progress_percent}`
                              : roadmapPercent == null
                                ? "—"
                                : `%${roadmapPercent}`}
                          </strong>
                        </div>
                        <WorkProgress
                          work={
                            roadmapPercent === undefined
                              ? objective?.work
                              : { ...objective?.work, progress_percent: roadmapPercent }
                          }
                        />
                        <p className="text-meta text-secondary">
                          Gerçek sonuç:{" "}
                          {objective?.strategic_progress_percent == null
                            ? "Henüz ölçülmedi"
                            : `%${objective.strategic_progress_percent}`}{" "}
                          · Hazırlık ilerlemesinden ayrı ölçülür.
                        </p>
                        <p className="text-meta text-muted">
                          {(scopeCounts?.total ?? objective?.work?.total_count)
                            ? `${scopeCounts?.completed ?? objective?.work?.completed_count}/${scopeCounts?.total ?? objective?.work?.total_count} ana adım tamamlandı`
                            : "Adım ekleyerek başlayabilirsin."}
                        </p>
                      </div>
                    ) : detail.isError ? (
                      <div role="alert">
                        Hedef alınamadı. <Button onClick={() => void detail.refetch()}>Yeniden dene</Button>
                      </div>
                    ) : (
                      <p role="status">Hedef yükleniyor…</p>
                    )}
                    {goal && (
                      <GoalLivingWorkspace
                        key={goal.id}
                        goalId={goal.id}
                        title={goal.title}
                        nodeId={requested}
                        onProgress={updateProgress}
                      />
                    )}
                    {objective && (
                      <Disclosure summary="Adımlar ve manuel ekleme">
                        <GoalWorkArea objective={objective} />
                      </Disclosure>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <Button onClick={() => setChatOpen(!chatOpen)} ariaExpanded={chatOpen}>
                        <img src="/brands/nous.png" alt="" className="h-5 w-5 rounded-full" /> Hermes’e ilerlememi sor
                      </Button>
                      <Button variant="ghost" onClick={() => setEvidenceOpen(true)}>
                        Ölçümler ve ayrıntılar
                      </Button>
                    </div>
                    {chatOpen && goal && (
                      <GoalStudio
                        key={`feedback:${goal.id}`}
                        goalId={goal.id}
                        goals={[]}
                        living
                        onClose={() => setChatOpen(false)}
                      />
                    )}
                  </>
                )}
                <Modal
                  open={createOpen}
                  onClose={() => setCreateOpen(false)}
                  title="Yeni hedef"
                  className="sm:max-w-2xl"
                >
                  <div className="stack-y-3">
                    <Button size="sm" variant="ghost" onClick={() => setManual(!manual)} ariaExpanded={manual}>
                      {manual ? "Hermes ile hazırla" : "Kendim oluştur"}
                    </Button>
                    {manual ? (
                      <GoalEditor
                        data={data}
                        onSaved={(id) => {
                          setSelected(id);
                          navigate(`/goals?entity=${encodeURIComponent(id)}`);
                          setCreateOpen(false);
                        }}
                      />
                    ) : (
                      <GoalStudio
                        goalId={null}
                        goals={[]}
                        living
                        longTerm={longTerm}
                        initialMessage={initialRequest || undefined}
                        onApplied={(id) => {
                          setSelected(id);
                          navigate(`/goals?entity=${encodeURIComponent(id)}`);
                          setCreateOpen(false);
                          setComposer("");
                        }}
                        onClose={() => setCreateOpen(false)}
                      />
                    )}
                  </div>
                </Modal>
                <Modal open={editOpen && Boolean(goal)} onClose={() => setEditOpen(false)} title="Hedefi düzenle">
                  {goal && <GoalEditor key={goal.id} goal={goal} data={data} onSaved={() => setEditOpen(false)} />}
                </Modal>
                <Modal
                  open={evidenceOpen && Boolean(objective)}
                  onClose={() => setEvidenceOpen(false)}
                  title="Ölçümler ve ayrıntılar"
                  className="sm:max-w-3xl"
                >
                  {objective && <ObjectiveEvidence objective={objective} providers={data.providers} />}
                </Modal>
                <Modal
                  open={advancedOpen}
                  onClose={() => setAdvancedOpen(false)}
                  title="Geçmiş ve gelişmiş ayarlar"
                  className="sm:max-w-3xl"
                >
                  <div className="stack-y-4">
                    <Tabs
                      value={view}
                      onChange={setView}
                      ariaLabel="Plan ayrıntıları"
                      items={[
                        { id: "plans", label: "Planlar" },
                        { id: "history", label: "Geçmiş" },
                        { id: "overview", label: "Strateji ayrıntıları" },
                      ]}
                    />
                    {view === "plans" && <PlanEditor data={data} requested={requested} />}
                    {view === "history" && (
                      <>
                        {history.isPending && <p role="status">Geçmiş yükleniyor…</p>}
                        {history.isError && <p role="alert">Geçmiş alınamadı.</p>}
                        {history.data && (
                          <>
                            <p className="text-meta text-secondary">{history.data.comparison_reason}</p>
                            {history.data.items.map((item) => (
                              <Disclosure key={item.id} summary={item.title}>
                                <pre className="overflow-auto text-meta">{JSON.stringify(item.state, null, 2)}</pre>
                              </Disclosure>
                            ))}
                          </>
                        )}
                      </>
                    )}
                    {view === "overview" && (
                      <>
                        <p className="text-body">Uyum: {percent(data.alignment.percent)}</p>
                        {data.warnings.map((r) => (
                          <p key={r.code} className="text-meta text-warn">
                            {r.explanation}
                          </p>
                        ))}
                        {data.findings.map((finding, i) => (
                          <Disclosure key={i} summary={finding.observed_facts}>
                            <p className="break-words text-meta">{finding.evidence_refs.join(" · ")}</p>
                          </Disclosure>
                        ))}
                      </>
                    )}
                  </div>
                </Modal>
              </>
            )}
          </div>
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

function WorkProgress({ work }: { work?: Partial<S["GoalWork"]> }) {
  return (
    <div
      role="progressbar"
      aria-label="Çalışma ilerlemesi"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={work?.progress_percent ?? undefined}
      aria-valuetext={work?.progress_percent == null ? "Henüz adım yok" : `%${work.progress_percent}`}
      className="h-2 overflow-hidden rounded-full bg-surface-sunken"
    >
      <div
        className="h-full rounded-full bg-accent transition motion-reduce:transition-none"
        style={{ width: `${work?.progress_percent ?? 0}%` }}
      />
    </div>
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
      <Input type="date" value={date} onChange={setDate} ariaLabel="Hedef tarihi" />
      <Disclosure summary="Diğer ayarlar">
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
      </Disclosure>
      <Button type="submit" disabled={!title.trim() || save.isPending}>
        {goal ? "Hedefi kaydet" : "Hedef oluştur"}
      </Button>
    </form>
  );
}

function ObjectiveEvidence({ objective: o, providers }: { objective: Objective; providers: Overview["providers"] }) {
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
          label="Çalışma ilerlemesi"
          value={percent(o.work?.progress_percent)}
          hint={`${o.work?.completed_count ?? 0}/${o.work?.total_count ?? 0} adım tamamlandı`}
        />
        <Metric label="Rota" value={pace[o.trajectory]} hint={`Beklenen ${percent(o.expected_percent)}`} />
        <Metric label="Kanıt kalitesi" value={confidence[o.confidence]} hint="Kullanıcı/model puanı değil" />
      </MetricStrip>
      {o.reasons.map((r, i) => (
        <p key={i} className="text-meta text-muted">
          {r.explanation}
        </p>
      ))}
      <h3 data-onboarding="goal-keyresults" className="text-heading">
        Ölçülebilir sonuçlar (Key Results)
      </h3>
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
      <p className="text-meta text-secondary">Beş yıllık yol haritanı yukarıda Hermes ile hazırlayabilirsin.</p>
      <Select value={id} onChange={setId} ariaLabel="Düzenlenecek plan">
        <option value="">Uzun vadeli planlar</option>
        {data.plans.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title} · r{p.revision}
          </option>
        ))}
      </Select>
      {id && !plan ? (
        <p role="status" className="text-meta text-muted">
          Plan yükleniyor…
        </p>
      ) : plan ? (
        <PlanForm key={id} plan={plan} onSaved={setId} />
      ) : (
        <Disclosure summary="Planı kendim oluştur">
          <PlanForm key="new" onSaved={setId} />
        </Disclosure>
      )}
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
