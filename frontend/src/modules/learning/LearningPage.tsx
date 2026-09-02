import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, FileJson, ListTodo, Network, Plus, Timer, Trash2 } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import type { Course, StudyArea, StudyTopic } from "@/core/types";
import { Button, Chip, Empty, IconButton, Input, PageFrame, PageHeader, Section, Toolbar, cx } from "@/core/ui";
import { RelatedPanel } from "@/core/RelatedPanel";
import { BacklinksPanel } from "@/core/BacklinksPanel";
import { confirmDialog } from "@/core/dialog";
import { planDayForToday } from "@/core/tasks";
import { useOnline } from "@/lib/hooks";
import { openPomodoro } from "@/modules/pomodoro/dock";
import { CoursesTab } from "./CoursesTab";
import { ResourceList } from "./ResourceList";
import { TopicNotes } from "./TopicNotes";
import { ImportDialog } from "./ImportDialog";
import { statusButtonClass, statusHint, statusLabel, statusTone, TOPIC_STATUSES } from "./learningLabels";

type TopicStats = { minutes: number; sessions: number };

type DetailTab = "resources" | "notes" | "links";
const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "resources", label: "Kaynaklar" },
  { id: "notes", label: "Notlar" },
  { id: "links", label: "Bağlantılar" },
];

/**
 * Ogrenme: calisma alani -> konu agaci (solda) + secili konunun kaynaklari
 * ve kurslar/kuyruk (sagda). Faz 12: study + learning tek modul; konu ile
 * kaynak arasi bag link uzerinden (learns_from).
 */
export function LearningPage() {
  const route = useHashRoute();
  // Deep-link: ?focus={id} konuyu acar (registry rotasi, Faz 32).
  const focusId = route.params.get("focus") ?? "";
  const [areaId, setAreaId] = useState("");
  const [areaTitle, setAreaTitle] = useState("");
  const [topicTitle, setTopicTitle] = useState("");
  const [selected, setSelected] = useState<StudyTopic | null>(null);
  const [subTitle, setSubTitle] = useState("");
  const [importing, setImporting] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("resources");
  const online = useOnline();
  const { data: areas = [] } = useQuery({
    queryKey: ["study-areas"],
    queryFn: () => api.get<StudyArea[]>("/study/areas"),
  });
  const { data: focusedTopic } = useQuery({
    queryKey: ["study-topic-focus", focusId],
    enabled: Boolean(focusId),
    queryFn: () => api.get<StudyTopic>(`/study/topics/${focusId}`),
  });
  useEffect(() => {
    if (!focusedTopic) return;
    setAreaId(focusedTopic.area_id);
    setSelected(focusedTopic);
  }, [focusedTopic]);
  useEffect(() => {
    if (!focusId && !areaId && areas[0]) setAreaId(areas[0].id);
  }, [areas, areaId, focusId]);
  const { data: topics = [] } = useQuery({
    queryKey: ["study-topics", areaId],
    enabled: Boolean(areaId),
    queryFn: () => api.get<StudyTopic[]>(`/study/topics?area_id=${areaId}`),
  });
  const { data: stats } = useQuery({
    queryKey: ["study-topic-stats", selected?.id],
    enabled: Boolean(selected),
    queryFn: () => api.get<TopicStats>(`/study/topics/${selected?.id}/stats`),
  });
  const { data: courses = [] } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });
  const addArea = useMutation({
    mutationFn: () => api.post("/study/areas", { title: areaTitle }),
    onSuccess: () => {
      setAreaTitle("");
      invalidateAfter("study.write");
    },
  });
  const addTopic = useMutation({
    mutationFn: () => api.post("/study/topics", { title: topicTitle, area_id: areaId }),
    onSuccess: () => {
      setTopicTitle("");
      invalidateAfter("study.write");
    },
  });
  const addSubTopic = useMutation({
    // Alt konu: ayni alan, parent_id secili konu (agac zaten parent_id tasiyor).
    mutationFn: () =>
      api.post("/study/topics", {
        title: subTitle,
        area_id: selected?.area_id,
        parent_id: selected?.id,
      }),
    onSuccess: () => {
      setSubTitle("");
      invalidateAfter("study.write");
    },
  });
  const removeTopic = useMutation({
    mutationFn: (id: string) => api.del(`/study/topics/${id}`),
    onSuccess: () => {
      setSelected(null);
      invalidateAfter("study.write");
    },
  });
  const removeArea = useMutation({
    mutationFn: (id: string) => api.del(`/study/areas/${id}`),
    onSuccess: (_data, id) => {
      if (id === areaId) setAreaId("");
      invalidateAfter("study.write");
    },
  });
  const createTask = useMutation({
    // Gorev + prepares_for bagi tek istekte (Faz 17); 'bugune al'
    // tercihi plan_day olarak uygulanir (Faz 31).
    mutationFn: (topic: StudyTopic) => api.post(`/study/topics/${topic.id}/todos`, { plan_day: planDayForToday() }),
    onSuccess: () => invalidateAfter("todo.write", "study.write", "link.write"),
  });
  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/study/topics/${selected?.id}`, body),
    onSuccess: () => invalidateAfter("study.write"),
  });
  const patchCourse = (id: string, progress_pct: number) => {
    coursePatch.mutate({
      id,
      progress_pct,
      status: progress_pct >= 100 ? "done" : undefined,
    });
  };
  const coursePatch = useMutation({
    mutationFn: ({ id, progress_pct, status }: { id: string; progress_pct: number; status?: string }) =>
      api.patch(`/courses/${id}`, { progress_pct, status }),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const removeCourse = (id: string) => courseRemove.mutate(id);
  const courseRemove = useMutation({
    mutationFn: (id: string) => api.del(`/courses/${id}`),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const confirmRemoveArea = async (area: StudyArea) => {
    const ok = await confirmDialog({
      title: `"${area.title}" silinsin mi?`,
      body: "İçindeki konular da gider.",
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) removeArea.mutate(area.id);
  };
  const confirmRemoveTopic = async (topic: StudyTopic) => {
    const ok = await confirmDialog({
      title: `"${topic.title}" silinsin mi?`,
      body: "Alt konuları da gider.",
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) removeTopic.mutate(topic.id);
  };
  /* Alanin ozeti: konu/kaynak/tamamlanan sayilari agactan turetilir --
     ayri bir uc cagirmaya gerek yok, agac zaten ilerlemeyi tasiyor. */
  const summary = topics.reduce(
    (acc, node) => {
      const walk = (item: StudyTopic) => {
        acc.topics += 1;
        if (item.status === "done") acc.done += 1;
        item.children?.forEach(walk);
      };
      walk(node);
      // progress kok konuda alt agaci da sayar; yalniz koklerden toplanir.
      acc.resources += node.progress?.total ?? 0;
      acc.completed += node.progress?.done ?? 0;
      return acc;
    },
    { topics: 0, done: 0, resources: 0, completed: 0 },
  );
  const overallPct = summary.resources ? Math.round((summary.completed / summary.resources) * 100) : 0;
  const currentAreaTitle = areas.find((area) => area.id === areaId)?.title ?? "Öğrenme alanı";

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Öğrenme"
        title="Çalışma"
        action={
          <div className="flex flex-wrap items-center gap-1.5">
            <Button onClick={() => setImporting((open) => !open)}>
              <FileJson size={14} /> JSON yükle
            </Button>
            <Button onClick={() => navigate("/graph")}>
              <Network size={14} /> Bilgi grafı
            </Button>
          </div>
        }
      />

      {importing && <ImportDialog areas={areas} onClose={() => setImporting(false)} />}

      {/* Alanlar sekme seridi: sol sutunu yiyip agaca yer birakiyordu. */}
      <Toolbar>
        {areas.map((area) => (
          <button
            key={area.id}
            type="button"
            onClick={() => {
              setAreaId(area.id);
              setSelected(null);
            }}
            className={cx(
              "group flex items-center gap-1.5 rounded-control border px-2.5 py-1 text-meta transition",
              areaId === area.id
                ? "border-accent-border bg-accent-surface font-medium text-accent"
                : "border-subtle text-secondary hover:bg-surface-hover hover:text-primary",
            )}
          >
            {area.title}
            <span
              role="button"
              tabIndex={-1}
              aria-label={`"${area.title}" alanını sil`}
              title="Alanı sil"
              onClick={(event) => {
                event.stopPropagation();
                confirmRemoveArea(area);
              }}
              className="text-muted opacity-0 transition group-hover:opacity-100 hover:text-danger"
            >
              <Trash2 size={12} />
            </span>
          </button>
        ))}
        <form
          className="ml-auto flex gap-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            if (areaTitle.trim()) addArea.mutate();
          }}
        >
          <Input value={areaTitle} onChange={setAreaTitle} placeholder="Yeni alan" className="h-8 w-40" />
          <Button size="sm" type="submit" disabled={!online || addArea.isPending}>
            <Plus size={13} />
          </Button>
        </form>
      </Toolbar>

      <div className="grid gap-5 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <div className="min-w-0 space-y-3">
          <LearningProgressSummary
            areaTitle={currentAreaTitle}
            topics={summary.topics}
            topicsDone={summary.done}
            resources={summary.resources}
            resourcesDone={summary.completed}
            minutes={stats?.minutes ?? 0}
            progressPct={overallPct}
          />
          <Section title="Konu ağacı" hint={topics.length ? `${summary.topics} konu` : undefined}>
            <TopicTreePanel
              topics={topics}
              online={online}
              onSelect={setSelected}
              selectedId={selected?.id ?? ""}
              onTask={(t) => createTask.mutate(t)}
              taskPending={createTask.isPending}
              title={topicTitle}
              onTitle={setTopicTitle}
              onAdd={() => addTopic.mutate()}
              areaId={areaId}
              pending={addTopic.isPending}
            />
          </Section>
        </div>

        {selected ? (
          <div className="min-w-0 space-y-5">
            <Section title="Konu ayrıntısı">
              <TopicDetailPanel
                selected={selected}
                stats={stats}
                online={online}
                onPatch={(body) => patch.mutate(body)}
                onRemove={() => confirmRemoveTopic(selected)}
              />
              <form
                className="mt-3 flex gap-2 border-t border-subtle pt-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (subTitle.trim()) addSubTopic.mutate();
                }}
              >
                <Input
                  value={subTitle}
                  onChange={setSubTitle}
                  placeholder={`"${selected.title}" altına alt konu`}
                  className="min-w-0 flex-1"
                />
                <Button type="submit" disabled={!online || addSubTopic.isPending}>
                  Alt konu ekle
                </Button>
              </form>
            </Section>

            {/* Sekmeler: kaynak/not/bag alt alta uzun bir sayfa yapiyordu. */}
            <Toolbar>
              {DETAIL_TABS.map((item) => (
                <Button
                  key={item.id}
                  size="sm"
                  variant={detailTab === item.id ? "primary" : "ghost"}
                  onClick={() => setDetailTab(item.id)}
                >
                  {item.label}
                </Button>
              ))}
            </Toolbar>
            {detailTab === "resources" && <ResourceList topicId={selected.id} />}
            {detailTab === "notes" && <TopicNotes topicId={selected.id} />}
            {detailTab === "links" && (
              <div className="space-y-5">
                <BacklinksPanel entityId={selected.id} />
                {/* Kaynaklar ve notlar kendi sekmelerinde; burada yalniz elle
                    kurulan diger baglar kalir (proje, gorev, medya...). */}
                <RelatedPanel entityId={selected.id} title="Bağlı kayıtlar" exclude={["learns_from", "notes_about"]} />
              </div>
            )}
          </div>
        ) : (
          <Empty variant="page" title="Bir konu seç">
            Soldaki ağaçtan bir konu seç — kaynakları, ilerlemesi ve notları burada açılır. Ya da yukarıdan JSON
            yükleyip hazır bir ağaç kur.
          </Empty>
        )}
      </div>

      <CoursesTab
        courses={courses}
        online={online}
        onProgress={(id, progress_pct) => patchCourse(id, progress_pct)}
        onRemove={(id) => removeCourse(id)}
      />
    </PageFrame>
  );
}

function LearningProgressSummary({
  areaTitle,
  topics,
  topicsDone,
  resources,
  resourcesDone,
  minutes,
  progressPct,
}: {
  areaTitle: string;
  topics: number;
  topicsDone: number;
  resources: number;
  resourcesDone: number;
  minutes: number;
  progressPct: number;
}) {
  const earnedXp = resourcesDone * 100;
  const totalXp = resources * 100;
  const complete = progressPct === 100 && resources > 0;

  return (
    <details open className="group overflow-hidden rounded-card border border-subtle bg-surface shadow-card">
      <summary className="cursor-pointer list-none px-3.5 py-3 [&::-webkit-details-marker]:hidden">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="label-caps">Öğrenme seviyesi</p>
            <p className="mt-0.5 truncate text-heading text-primary">{areaTitle}</p>
          </div>
          <span className={cx("numeral text-numeral-lg", complete ? "text-ok" : "text-accent")}>%{progressPct}</span>
          <ChevronDown
            size={15}
            aria-hidden="true"
            className="mt-1 text-muted transition-transform group-open:rotate-180"
          />
        </div>
        <div className="mt-3 flex items-center justify-between gap-3 text-meta">
          <span className="text-secondary">XP ilerlemesi</span>
          <span className="numeral text-muted">
            {earnedXp} / {totalXp} XP
          </span>
        </div>
        <div
          role="progressbar"
          aria-label={`${areaTitle} öğrenme ilerlemesi`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progressPct}
          className="mt-1.5 h-2.5 overflow-hidden rounded-control bg-surface-sunken"
        >
          <span
            className={cx(
              "block h-full rounded-control transition-[width] duration-500",
              complete ? "bg-ok" : "bg-accent",
            )}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </summary>

      <div className="grid grid-cols-3 divide-x divide-subtle border-t border-subtle bg-surface-sunken/40 px-1 py-2.5">
        <LearningProgressStat value={topics} label="konu" hint={`${topicsDone} bitti`} />
        <LearningProgressStat value={resources} label="kaynak" hint={`${resourcesDone} bitti`} />
        <LearningProgressStat value={`${minutes} dk`} label="odak" hint="seçili konu" />
      </div>
    </details>
  );
}

function LearningProgressStat({ value, label, hint }: { value: number | string; label: string; hint: string }) {
  return (
    <div className="min-w-0 px-2 text-center">
      <p className="numeral truncate text-heading text-primary">{value}</p>
      <p className="text-meta text-secondary">{label}</p>
      <p className="truncate text-micro text-muted">{hint}</p>
    </div>
  );
}

function AreasPanel({
  areas,
  areaId,
  online,
  onSelect,
  onRemoveArea,
  title,
  onTitle,
  onAdd,
  pending,
  addPending,
}: {
  areas: StudyArea[];
  areaId: string;
  online: boolean;
  onSelect: (id: string) => void;
  onRemoveArea: (area: StudyArea) => void;
  title: string;
  onTitle: (value: string) => void;
  onAdd: () => void;
  pending: boolean;
  addPending: boolean;
}) {
  return (
    <>
      <div className="divide-y divide-subtle border-y border-subtle">
        {areas.map((a) => (
          <div
            key={a.id}
            className={cx("group flex items-center", areaId === a.id && "bg-accent-surface text-primary")}
          >
            <button
              onClick={() => onSelect(a.id)}
              className={cx(
                "min-w-0 flex-1 truncate px-2 py-2 text-left text-body hover:bg-surface-hover",
                areaId === a.id && "bg-accent-surface text-primary",
              )}
            >
              {a.title}
            </button>
            <IconButton
              title="Alanı sil"
              tone="danger"
              disabled={!online || pending}
              onClick={() => onRemoveArea(a)}
              className="mr-1.5 h-6 w-6 opacity-0 transition group-hover:opacity-100"
            >
              <Trash2 size={13} />
            </IconButton>
          </div>
        ))}
      </div>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim()) onAdd();
        }}
      >
        <Input value={title} onChange={onTitle} className="min-w-0 flex-1" placeholder="Yeni alan" />
        <Button type="submit" disabled={!online || addPending}>
          +
        </Button>
      </form>
    </>
  );
}

function TopicTreePanel({
  topics,
  online,
  onSelect,
  selectedId,
  onTask,
  taskPending,
  title,
  onTitle,
  onAdd,
  areaId,
  pending,
}: {
  topics: StudyTopic[];
  online: boolean;
  onSelect: (topic: StudyTopic) => void;
  selectedId: string;
  onTask: (topic: StudyTopic) => void;
  taskPending: boolean;
  title: string;
  onTitle: (value: string) => void;
  onAdd: () => void;
  areaId: string;
  pending: boolean;
}) {
  return (
    <>
      {topics.length ? (
        <TopicTree
          items={topics}
          select={onSelect}
          selectedId={selectedId}
          taskPending={taskPending}
          onTask={onTask}
          onFocus={(topic) => openPomodoro({ context: topic.id, topic: topic.title })}
        />
      ) : (
        <Empty>Konu yok.</Empty>
      )}
      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim() && areaId) onAdd();
        }}
      >
        <Input value={title} onChange={onTitle} className="min-w-0 flex-1" placeholder="Yeni kök konu" />
        <Button type="submit" disabled={!online || pending}>
          Ekle
        </Button>
      </form>
    </>
  );
}

function TopicDetailPanel({
  selected,
  stats,
  online,
  onPatch,
  onRemove,
}: {
  selected: StudyTopic;
  stats?: TopicStats;
  online: boolean;
  onPatch: (body: Record<string, unknown>) => void;
  onRemove: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-medium">{selected.title}</h2>
          <p className="text-meta text-muted">
            {stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} seans
          </p>
        </div>
        <IconButton title="Konuyu sil" tone="danger" disabled={!online} onClick={onRemove}>
          <Trash2 size={14} />
        </IconButton>
      </div>
      <div>
        <p className="mb-1.5 text-meta text-secondary">Durum</p>
        {/* Segment kontrolu: uc secenek de gorunur, tek tikla degisir.
            Acilir liste secenekleri gizliyordu ve ne anlama geldikleri
            belirsizdi. */}
        <div
          role="radiogroup"
          aria-label="Konu durumu"
          className="inline-flex rounded-control border border-subtle bg-surface-sunken p-0.5"
        >
          {TOPIC_STATUSES.map((value) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={selected.status === value}
              disabled={!online}
              onClick={() => onPatch({ status: value })}
              className={cx(
                "rounded-control border px-3 py-1 text-meta transition disabled:cursor-not-allowed disabled:opacity-40",
                statusButtonClass(value, selected.status === value),
              )}
            >
              {statusLabel(value)}
            </button>
          ))}
        </div>
        <p className="mt-1.5 text-meta text-muted">{statusHint(selected.status)}</p>
      </div>
      <Button variant="primary" onClick={() => openPomodoro({ context: selected.id, topic: selected.title })}>
        Pomodoro başlat
      </Button>
    </div>
  );
}

function TopicTree({
  items,
  select,
  selectedId,
  depth = 0,
  onTask,
  onFocus,
  taskPending,
}: {
  items: StudyTopic[];
  select: (t: StudyTopic) => void;
  selectedId: string;
  depth?: number;
  onTask: (t: StudyTopic) => void;
  onFocus: (t: StudyTopic) => void;
  taskPending: boolean;
}) {
  const online = useOnline();
  return (
    <div>
      {items.map((t) => (
        <div key={t.id}>
          <div
            className={cx(
              "group flex w-full items-center gap-1 rounded-control pr-1 transition",
              selectedId === t.id ? "bg-accent-surface" : "hover:bg-surface-hover",
            )}
          >
            <button
              onClick={() => select(t)}
              style={{ paddingLeft: `${depth * 16 + 8}px` }}
              className="min-w-0 flex-1 py-2 text-left text-body"
            >
              <span className="block truncate">{t.title}</span>
              {/* Kaynak sayacindan turetilen ilerleme -- alt konular dahil. */}
              {t.progress && t.progress.total > 0 && (
                <span className="mt-0.5 flex items-center gap-1.5">
                  <span className="h-1 w-16 overflow-hidden rounded-control bg-surface-sunken">
                    <span
                      className={cx("block h-full rounded-control", t.progress.pct === 100 ? "bg-ok" : "bg-accent")}
                      style={{ width: `${t.progress.pct}%` }}
                    />
                  </span>
                  <span className="numeral text-micro text-muted">
                    {t.progress.done}/{t.progress.total}
                  </span>
                </span>
              )}
            </button>
            <span className="flex shrink-0 items-center gap-0.5">
              <button
                type="button"
                title="Görev oluştur"
                aria-label={`"${t.title}" için görev oluştur`}
                disabled={!online || taskPending}
                onClick={() => onTask(t)}
                className={cx(
                  "flex h-7 w-7 items-center justify-center rounded-control text-muted transition",
                  "hover:bg-surface-sunken hover:text-primary disabled:cursor-not-allowed disabled:opacity-40",
                )}
              >
                <ListTodo size={13} />
              </button>
              <button
                type="button"
                title="Odaklan"
                aria-label={`"${t.title}" için odaklan`}
                disabled={!online}
                onClick={() => onFocus(t)}
                className={cx(
                  "flex h-7 w-7 items-center justify-center rounded-control text-muted transition",
                  "hover:bg-surface-sunken hover:text-primary disabled:cursor-not-allowed disabled:opacity-40",
                )}
              >
                <Timer size={13} />
              </button>
              <Chip tone={statusTone(t.status)}>{statusLabel(t.status)}</Chip>
            </span>
          </div>
          <TopicTree
            items={t.children ?? []}
            select={select}
            selectedId={selectedId}
            depth={depth + 1}
            onTask={onTask}
            onFocus={onFocus}
            taskPending={taskPending}
          />
        </div>
      ))}
    </div>
  );
}
