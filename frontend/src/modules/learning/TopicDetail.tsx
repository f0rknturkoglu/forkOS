import { ContextualHelp } from "@/core/ContextualHelp";
/**
 * Konu calisma alani (master-detail'in sag paneli).
 *
 * Ust blok ILK EKRANDA, kaydirmadan: breadcrumb, baslik, durum ve DORT AYRI
 * olcu (kaynak ilerlemesi, odak suresi, ustalik, hedef sure). Bu olcumler tek
 * bir yuzdeye INDIRGENMEZ -- her biri farkli soruyu yanitlar.
 *
 * "Siradaki aksiyon" tek birincil dugmedir ve baglama gore degisir; secim
 * mantigi `pickNextAction` saf fonksiyonunda (test edilebilir).
 *
 * Sekmeler ve icerikleri burada; sayfa kabugu (rail, URL, basliğin ust
 * yerlesimi) `LearningPage`'de (LF1).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Baby,
  ChevronRight,
  ExternalLink,
  FolderInput,
  ListPlus,
  MoreHorizontal,
  Pencil,
  Play,
  ScrollText,
  Timer,
  Trash2,
} from "lucide-react";
import { api, ApiError } from "@/core/api";
import { BacklinksPanel } from "@/core/BacklinksPanel";
import { RelatedPanel } from "@/core/RelatedPanel";
import { invalidateAfter } from "@/core/invalidation";
import { safeHref } from "@/core/markdownParser";
import {
  Button,
  Chip,
  Empty,
  Field,
  IconButton,
  Input,
  Metric,
  MetricStrip,
  Modal,
  NumberInput,
  Popover,
  SectionHeader,
  Select,
  Skeleton,
  SkeletonRows,
  Tabs,
  cx,
  relativeTime,
  useToast,
} from "@/core/ui";
import { navigate } from "@/app/router";
import { planDayForToday } from "@/core/tasks";
import { statusButtonClass, statusLabel, statusTone, TOPIC_STATUSES } from "./learningLabels";
import { ImpactDialog } from "./ImpactDialog";
import { ResourceList, TopicProgressBar } from "./ResourceList";
import { ReviewPanel } from "./ReviewPanel";
import { TopicKnowledgeNote } from "./TopicKnowledgeNote";
import type { components } from "@/generated/api-schema";
import { formatTrDate } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { openPomodoro } from "@/modules/pomodoro/dock";

type StudyTopicDetailOut = components["schemas"]["StudyTopicDetailOut"];
type ResourceOut = components["schemas"]["ResourceOut"];
type StudyTopicNode = components["schemas"]["StudyTopicNode"];
type TopicTodoOut = components["schemas"]["TopicTodoOut"];

export type TopicTab = "genel" | "kaynaklar" | "notlar" | "baglantilar" | "tekrar";

const TOPIC_TABS: { id: TopicTab; label: string }[] = [
  { id: "genel", label: "Genel" },
  { id: "kaynaklar", label: "Kaynaklar" },
  { id: "notlar", label: "Notlar" },
  { id: "baglantilar", label: "Bağlantılar" },
  { id: "tekrar", label: "Tekrar" },
];

type NextActionId = "todo" | "pomodoro" | "review" | "start" | "next-resource" | "refresh";

export interface NextActionInput {
  /** Konunun acik gorevi (detail'den). */
  openTodo: { id: string } | null;
  /** Bu konu baglaminda suren pomodoro seansi var mi. */
  pomodoroActive: boolean;
  /** SRS vadesi geldi mi. */
  reviewDue: boolean;
  status: string;
  resourceDone: number;
  resourceTotal: number;
}

/** Baglama gore TEK birincil aksiyon. Sirada ilk uyan kazanir. */
export function pickNextAction(input: NextActionInput): { id: NextActionId; label: string } {
  if (input.openTodo) return { id: "todo", label: "Görevi aç" };
  if (input.pomodoroActive) return { id: "pomodoro", label: "Odağa dön" };
  if (input.reviewDue) return { id: "review", label: "Tekrar yap" };
  if (input.resourceDone === 0) return { id: "start", label: "Çalışmaya başla" };
  if (input.resourceDone < input.resourceTotal) return { id: "next-resource", label: "Sıradaki kaynağı aç" };
  if (input.status === "done") return { id: "refresh", label: "Bilgiyi tazele" };
  return { id: "start", label: "Çalışmaya başla" };
}

/** Ilk tamamlanmamis kaynak: "Siradaki kaynagi ac" bunu acar. */
const firstOpenResource = (resources: ResourceOut[]) => resources.find((resource) => !resource.completed_at) ?? null;

function StatusSegment({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (status: string) => void;
  disabled?: boolean;
}) {
  return (
    <div role="group" aria-label="Konu durumu" className="inline-flex rounded-control border border-subtle p-0.5">
      {TOPIC_STATUSES.map((status) => (
        <button
          key={status}
          type="button"
          aria-pressed={value === status}
          disabled={disabled}
          onClick={() => onChange(status)}
          title={statusLabel(status)}
          className={cx(
            "h-7 rounded-control border px-2.5 text-meta transition",
            statusButtonClass(status, value === status),
            disabled && "cursor-not-allowed opacity-40",
          )}
        >
          {statusLabel(status)}
        </button>
      ))}
    </div>
  );
}

function ConfidenceSegment({
  value,
  onChange,
  disabled,
}: {
  value: number | null;
  onChange: (next: number) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="group"
      aria-label="Güven düzeyi (1-5)"
      className="inline-flex rounded-control border border-subtle p-0.5"
    >
      {[1, 2, 3, 4, 5].map((level) => (
        <button
          key={level}
          type="button"
          aria-pressed={value === level}
          aria-label={`Güven ${level}/5`}
          disabled={disabled}
          onClick={() => onChange(level)}
          className={cx(
            "h-7 w-7 rounded-control border text-meta tabular-nums transition",
            value === level
              ? "border-accent-border bg-accent-surface font-medium text-accent"
              : "border-transparent text-secondary hover:bg-surface-hover hover:text-primary",
            disabled && "cursor-not-allowed opacity-40",
          )}
        >
          {level}
        </button>
      ))}
    </div>
  );
}

export function TopicDetail({
  topicId,
  tab,
  onTabChange,
  onDeleted,
}: {
  topicId: string;
  tab: TopicTab;
  onTabChange: (next: TopicTab) => void;
  onDeleted: () => void;
}) {
  const online = useOnline();
  const toast = useToast();
  const [addResourceSignal, setAddResourceSignal] = useState(0);
  const [subTopicOpen, setSubTopicOpen] = useState(false);
  const [subTopicTitle, setSubTopicTitle] = useState("");
  const [moveOpen, setMoveOpen] = useState(false);
  const [moveParent, setMoveParent] = useState("");
  const [moveError, setMoveError] = useState("");
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTitle, setRenameTitle] = useState("");
  const [impactOpen, setImpactOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuAnchor = useRef<HTMLSpanElement | null>(null);
  const [masteryDraft, setMasteryDraft] = useState(0);
  const [confirmingDone, setConfirmingDone] = useState(false);
  const [targetDraft, setTargetDraft] = useState(0);

  const {
    data: detail,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["study-topic", topicId],
    enabled: Boolean(topicId),
    queryFn: () => api.get<StudyTopicDetailOut>(`/study/topics/${topicId}`),
  });

  const topic = detail?.topic;
  const areaId = topic?.area_id ?? "";

  /* Odağa dön: yalnizca BU konu baglaminda akan seans "aktif" sayilir. */
  const { data: activePomodoro = null } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<components["schemas"]["PomodoroOut"] | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });
  const pomodoroActive = Boolean(
    activePomodoro && !activePomodoro.ended_at && activePomodoro.context_entity_id === topicId,
  );

  const { data: treeNodes = [] } = useQuery({
    queryKey: ["study-tree", areaId],
    enabled: moveOpen && Boolean(areaId),
    queryFn: async () =>
      (await api.get<components["schemas"]["StudyTreeOut"]>(`/study/areas/${areaId}/tree`)).nodes ?? [],
  });

  useEffect(() => {
    if (topic) setTargetDraft(topic.target_min ?? 0);
  }, [topic?.id, topic?.target_min]);

  const refresh = () => invalidateAfter("study.write");

  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/study/topics/${topicId}`, body),
    onSuccess: refresh,
  });

  const createTodo = useMutation({
    mutationFn: () => api.post<TopicTodoOut>(`/study/topics/${topicId}/todos`, { plan_day: planDayForToday() }),
    onSuccess: (result) => {
      invalidateAfter("todo.write", "study.write");
      toast.push(result.created ? "Görev oluşturuldu." : "Bu konunun açık görevi açıldı.", {
        tone: result.created ? "ok" : "neutral",
        action: { label: "Görevi aç", run: () => navigate(`/todos?focus=${result.todo.id}`) },
      });
    },
  });

  const addSubTopic = useMutation({
    mutationFn: () => api.post("/study/topics", { title: subTopicTitle.trim(), area_id: areaId, parent_id: topicId }),
    onSuccess: () => {
      setSubTopicTitle("");
      setSubTopicOpen(false);
      refresh();
    },
  });

  const move = useMutation({
    mutationFn: (parentId: string) => api.post(`/study/topics/${topicId}/move`, { parent_id: parentId || null }),
    onSuccess: () => {
      setMoveOpen(false);
      setMoveError("");
      refresh();
    },
    onError: (mutationError) => {
      // Dongu/alan ihlali 422 olarak doner; mesaj kullaniciya aynen gosterilir.
      setMoveError(mutationError instanceof ApiError ? mutationError.message : "Taşınamadı.");
    },
  });

  const candidates = useMemo(() => {
    // Kendisi ve alt soyu hedef olamaz (backend de 422 ile reddeder).
    return treeNodes.filter((node: StudyTopicNode) => node.id !== topicId && !(node.path ?? []).includes(topicId));
  }, [treeNodes, topicId]);

  if (isLoading) {
    return (
      <div className="stack-y-4" aria-busy>
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-24 w-full" />
        <SkeletonRows rows={4} />
      </div>
    );
  }

  if (error || !detail || !topic) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <Empty variant="page" title={notFound ? "Konu bulunamadı" : "Konu yüklenemedi"}>
        {notFound ? "Bu konu silinmiş ya da bağlantı eskimiş olabilir." : "Bağlantını kontrol edip tekrar dene."}
      </Empty>
    );
  }

  const stats = detail.stats;
  const nextAction = pickNextAction({
    openTodo: detail.open_todo ?? null,
    pomodoroActive,
    reviewDue: detail.review.due,
    status: topic.status,
    resourceDone: detail.progress.done,
    resourceTotal: detail.progress.total,
  });
  const nextResource = firstOpenResource(detail.resources ?? []);
  const nextHref = nextResource?.url ? safeHref(nextResource.url) : null;

  const runNextAction = () => {
    switch (nextAction.id) {
      case "todo":
        return navigate(`/todos?focus=${detail.open_todo?.id ?? ""}`);
      case "pomodoro":
      case "start":
        return openPomodoro({ context: topic.id, topic: topic.title });
      case "review":
      case "refresh":
        return onTabChange("tekrar");
      case "next-resource":
        if (!nextResource) return;
        void api.get(`/learning/resources/${nextResource.id}`).catch(() => undefined);
        if (nextHref) return window.open(nextHref, "_blank", "noopener,noreferrer");
        return onTabChange("kaynaklar");
    }
  };

  const applyStatus = (status: string) => {
    if (status === "done") {
      setMasteryDraft(topic.mastery ?? 0);
      setConfirmingDone(true);
      return;
    }
    setConfirmingDone(false);
    patch.mutate({ status });
  };

  return (
    <div className="stack-y-5">
      <ContextualHelp
        key={topicId}
        context={{ kind: "learning", entity_id: topicId }}
        label="Bu konudan nasıl devam edebilirim?"
      />
      <header className="stack-y-2">
        <nav aria-label="Konu yolu" className="flex flex-wrap items-center gap-1 text-meta text-muted">
          {(detail.ancestors ?? []).map((ancestor) => (
            <span key={ancestor.id} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => navigate(`/learning?focus=${ancestor.id}`)}
                className="max-w-40 truncate rounded-control px-1 transition hover:text-accent"
              >
                {ancestor.title}
              </button>
              <ChevronRight size={12} aria-hidden />
            </span>
          ))}
          <span className="truncate text-secondary">{topic.title}</span>
        </nav>

        <div className="flex flex-wrap items-center gap-2">
          <h1 className="min-w-0 truncate text-title text-primary">{topic.title}</h1>
          <Chip tone={statusTone(topic.status)}>{statusLabel(topic.status)}</Chip>
          {detail.open_todo && (
            <Chip size="xs" tone="accent">
              Açık görev
            </Chip>
          )}
        </div>

        <MetricStrip className="grid-cols-2 lg:grid-cols-4">
          <div className="min-w-0 px-3.5 py-3 sm:px-4">
            <TopicProgressBar
              done={detail.progress.done}
              total={detail.progress.total}
              pct={detail.progress.pct}
              label="Kaynak ilerlemesi"
            />
          </div>
          <Metric
            label="Odak süresi"
            value={`${stats.minutes} dk`}
            hint={`${stats.sessions} seans · ${stats.week_minutes} dk bu hafta`}
          />
          <Metric
            label="Ustalık"
            value={topic.mastery !== null ? `%${topic.mastery}` : "—"}
            hint={`Güven: ${topic.confidence ? `${topic.confidence}/5` : "—"}`}
          />
          <Metric
            label="Hedef süre"
            value={topic.target_min ? `${topic.target_min} dk` : "—"}
            hint={stats.last_studied_at ? `Son çalışma ${relativeTime(stats.last_studied_at)}` : "Henüz çalışılmadı"}
          />
        </MetricStrip>

        <div className="flex flex-wrap items-center gap-1.5">
          <Button variant="primary" disabled={!online} onClick={runNextAction}>
            {nextAction.id === "todo" ? <ListPlus size={14} /> : <Play size={14} />}
            {nextAction.label}
          </Button>
          <Button disabled={!online} onClick={() => openPomodoro({ context: topic.id, topic: topic.title })}>
            <Timer size={14} /> Pomodoro
          </Button>
          <Button disabled={!online || createTodo.isPending} onClick={() => createTodo.mutate()}>
            <ListPlus size={14} /> Görev oluştur
          </Button>
          <Button
            disabled={!online}
            onClick={() => {
              setAddResourceSignal((count) => count + 1);
              onTabChange("kaynaklar");
            }}
          >
            <ScrollText size={14} /> Kaynak ekle
          </Button>
          <Button disabled={!online} onClick={() => setSubTopicOpen(true)}>
            <Baby size={14} /> Alt konu ekle
          </Button>
          <Button disabled={!online} onClick={() => setMoveOpen(true)}>
            <FolderInput size={14} /> Taşı
          </Button>
          <span ref={menuAnchor} className="relative inline-flex">
            <IconButton
              title="Daha fazla"
              disabled={!online}
              className={cx(menuOpen && "bg-surface-hover text-primary")}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <MoreHorizontal size={14} />
            </IconButton>
            <Popover
              open={menuOpen}
              onClose={() => setMenuOpen(false)}
              anchorRef={menuAnchor}
              role="menu"
              ariaLabel="Konu işlemleri"
              className="right-0 top-full mt-1 w-44 py-1"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setRenameTitle(topic.title);
                  setRenameOpen(true);
                  setMenuOpen(false);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-meta text-primary transition hover:bg-surface-hover"
              >
                <Pencil size={13} /> Yeniden adlandır
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setImpactOpen(true);
                  setMenuOpen(false);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-meta text-danger transition hover:bg-danger-surface"
              >
                <Trash2 size={13} /> Sil
              </button>
            </Popover>
          </span>
        </div>
      </header>

      <Tabs
        value={tab}
        onChange={onTabChange}
        items={TOPIC_TABS.map((item) => ({ id: item.id, label: item.label }))}
        ariaLabel="Konu sekmeleri"
      />

      <div role="tabpanel" aria-label={TOPIC_TABS.find((item) => item.id === tab)?.label ?? "Genel"}>
        {tab === "genel" && (
          <div className="stack-y-5">
            <section className="stack-y-3">
              <SectionHeader label="Durum" />
              <div className="flex flex-wrap items-center gap-3">
                <StatusSegment value={topic.status} onChange={applyStatus} disabled={!online || patch.isPending} />
                <span className="text-meta text-muted">{statusLabel(topic.status)}</span>
              </div>
              {confirmingDone && (
                <div className="flex flex-wrap items-end gap-3 rounded-card border border-subtle bg-surface p-3">
                  <Field label="Ustalık (%)" hint="Öğrenildi işaretlerken ustalık sorulur.">
                    <NumberInput
                      value={masteryDraft}
                      onChange={setMasteryDraft}
                      min={0}
                      max={100}
                      step={5}
                      ariaLabel="Ustalık yüzdesi"
                      className="w-28"
                    />
                  </Field>
                  <Button
                    variant="primary"
                    disabled={!online || patch.isPending}
                    onClick={() => {
                      patch.mutate({ status: "done", mastery: masteryDraft });
                      setConfirmingDone(false);
                    }}
                  >
                    Öğrenildi olarak işaretle
                  </Button>
                  <Button onClick={() => setConfirmingDone(false)}>Vazgeç</Button>
                </div>
              )}
            </section>

            <section className="stack-y-3">
              <SectionHeader label="Değerlendirme" />
              <div className="flex flex-wrap items-center gap-3">
                <ConfidenceSegment
                  value={topic.confidence ?? null}
                  disabled={!online || patch.isPending}
                  onChange={(confidence) => patch.mutate({ confidence })}
                />
                <span className="text-meta text-muted">Güven 1-5</span>
              </div>
              <div className="flex flex-wrap items-end gap-3">
                <Field label="Hedef süre (dk)">
                  <NumberInput
                    value={targetDraft}
                    onChange={setTargetDraft}
                    min={0}
                    step={5}
                    ariaLabel="Hedef süre (dakika)"
                    className="w-28"
                  />
                </Field>
                <Button
                  disabled={!online || patch.isPending || targetDraft === (topic.target_min ?? 0)}
                  onClick={() => patch.mutate({ target_min: targetDraft > 0 ? targetDraft : null })}
                >
                  Kaydet
                </Button>
              </div>
            </section>

            <section className="stack-y-3">
              <SectionHeader label="Özet" />
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-body sm:grid-cols-4">
                <div>
                  <dt className="text-meta text-muted">Son çalışma</dt>
                  <dd className="font-medium text-primary">
                    {stats.last_studied_at ? relativeTime(stats.last_studied_at) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-meta text-muted">Sonraki tekrar</dt>
                  <dd className="font-medium text-primary">
                    {detail.review.next_review_at
                      ? formatTrDate(detail.review.next_review_at)
                      : detail.review.due
                        ? "Bugün"
                        : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-meta text-muted">Flashcard destesi</dt>
                  <dd className="font-medium text-primary">{detail.flashcard_deck_count}</dd>
                </div>
              </dl>
            </section>

            {detail.open_todo && (
              <section className="stack-y-2">
                <SectionHeader label="Açık görev" />
                <div className="flex flex-wrap items-center gap-2 rounded-card border border-subtle bg-surface p-3">
                  <span className="min-w-0 flex-1 truncate text-body text-primary">{detail.open_todo.title}</span>
                  {detail.open_todo.due_at && (
                    <Chip size="xs" tone="warn">
                      {formatTrDate(detail.open_todo.due_at)}
                    </Chip>
                  )}
                  <a
                    href={`#/todos?focus=${detail.open_todo.id}`}
                    className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-control border border-strong bg-surface px-3 text-meta font-medium text-primary transition hover:bg-surface-hover"
                  >
                    <ExternalLink size={13} /> Görevi aç
                  </a>
                </div>
              </section>
            )}
          </div>
        )}

        {tab === "kaynaklar" && <ResourceList topicId={topicId} addSignal={addResourceSignal} />}

        {tab === "notlar" && <TopicKnowledgeNote topicId={topicId} topicTitle={topic.title} />}

        {tab === "baglantilar" && (
          <div className="stack-y-5">
            <RelatedPanel entityId={topicId} title="Bağlı kayıtlar" exclude={["learns_from", "notes_about"]} />
            <BacklinksPanel entityId={topicId} />
          </div>
        )}

        {tab === "tekrar" && (
          <ReviewPanel
            topicId={topicId}
            review={detail.review}
            confidence={topic.confidence ?? null}
            lastStudiedAt={stats.last_studied_at ?? null}
          />
        )}
      </div>

      <Modal
        open={subTopicOpen}
        onClose={() => setSubTopicOpen(false)}
        title="Alt konu ekle"
        hint={`"${topic.title}" altına yeni konu.`}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setSubTopicOpen(false)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !subTopicTitle.trim() || addSubTopic.isPending}
              onClick={() => addSubTopic.mutate()}
            >
              Ekle
            </Button>
          </div>
        }
      >
        <Field label="Konu başlığı">
          <Input
            value={subTopicTitle}
            onChange={setSubTopicTitle}
            placeholder="Örn. merge conflict çözümü"
            className="w-full"
          />
        </Field>
      </Modal>

      <Modal
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
        title="Konuyu taşı"
        hint="Kendi alt ağacının içine taşınamaz."
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setMoveOpen(false)}>Vazgeç</Button>
            <Button variant="primary" disabled={!online || move.isPending} onClick={() => move.mutate(moveParent)}>
              Taşı
            </Button>
          </div>
        }
      >
        <Field label="Yeni üst konu">
          <Select value={moveParent} onChange={setMoveParent} ariaLabel="Yeni üst konu" className="w-full">
            <option value="">Kök (üst konu yok)</option>
            {candidates.map((node) => (
              <option key={node.id} value={node.id}>
                {"— ".repeat(node.depth)}
                {node.title}
              </option>
            ))}
          </Select>
        </Field>
        {moveError && (
          <p role="alert" className="mt-3 text-meta text-danger">
            {moveError}
          </p>
        )}
      </Modal>

      <Modal
        open={renameOpen}
        onClose={() => setRenameOpen(false)}
        title="Konuyu yeniden adlandır"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setRenameOpen(false)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !renameTitle.trim() || patch.isPending}
              onClick={() => {
                patch.mutate({ title: renameTitle.trim() });
                setRenameOpen(false);
              }}
            >
              Kaydet
            </Button>
          </div>
        }
      >
        <Field label="Başlık">
          <Input value={renameTitle} onChange={setRenameTitle} className="w-full" />
        </Field>
      </Modal>

      <ImpactDialog
        topicId={topicId}
        topicTitle={topic.title}
        open={impactOpen}
        onClose={() => setImpactOpen(false)}
        onDeleted={onDeleted}
      />
    </div>
  );
}
