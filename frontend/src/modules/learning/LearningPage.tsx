import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ListTodo, Timer, Trash2 } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import type { Bookmark, Course, StudyArea, StudyTopic } from "@/core/types";
import { Button, Chip, Empty, Field, IconButton, Input, PageFrame, PageHeader, Section, Select, cx } from "@/core/ui";
import { RelatedPanel } from "@/core/RelatedPanel";
import { confirmDialog } from "@/core/dialog";
import { planDayForToday } from "@/core/tasks";
import { useOnline } from "@/lib/hooks";
import { CoursesTab } from "./CoursesTab";
import { QueueTab } from "./QueueTab";

type TopicStats = { minutes: number; sessions: number };

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
  const online = useOnline();
  const { data: areas = [] } = useQuery({
    queryKey: ["study-areas"],
    queryFn: () => api.get<StudyArea[]>("/study/areas"),
  });
  useEffect(() => {
    if (!areaId && areas[0]) setAreaId(areas[0].id);
  }, [areas, areaId]);
  const { data: topics = [] } = useQuery({
    queryKey: ["study-topics", areaId],
    enabled: Boolean(areaId),
    queryFn: () => api.get<StudyTopic[]>(`/study/topics?area_id=${areaId}`),
  });
  // Deep-link: focus konusu yuklendiginde sec (bulundugu alani da ac).
  useEffect(() => {
    if (!focusId) return;
    const topic = topics.find((item) => item.id === focusId);
    if (topic) {
      setAreaId(topic.area_id ?? areaId);
      setSelected(topic);
    }
  }, [focusId, topics, areaId]);
  const { data: stats } = useQuery({
    queryKey: ["study-topic-stats", selected?.id],
    enabled: Boolean(selected),
    queryFn: () => api.get<TopicStats>(`/study/topics/${selected?.id}/stats`),
  });
  const { data: courses = [] } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });
  const { data: queue = [] } = useQuery({
    queryKey: ["learning-queue"],
    queryFn: () => api.get<Bookmark[]>("/learning/queue"),
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
  const moveQueue = (id: string, queue_kind: string) => queueMove.mutate({ id, queue_kind });
  const queueMove = useMutation({
    mutationFn: ({ id, queue_kind }: { id: string; queue_kind: string }) =>
      api.patch(`/bookmarks/${id}`, { queue_kind }),
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
  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Takip" title="Çalışma" />
      <p className="text-meta text-muted">Alan → konu ağacı; odak süreleri Pomodoro’dan türetilir.</p>
      <div
        className={cx(
          "grid min-w-0 divide-y divide-subtle border-y border-subtle",
          "lg:grid-cols-[15rem_minmax(0,1fr)_18rem] lg:divide-x lg:divide-y-0",
        )}
      >
        <Section title="Alanlar" className="min-w-0 py-3 lg:pr-4">
          <AreasPanel
            areas={areas}
            areaId={areaId}
            online={online}
            onSelect={(id) => {
              setAreaId(id);
              setSelected(null);
            }}
            onRemoveArea={confirmRemoveArea}
            title={areaTitle}
            onTitle={setAreaTitle}
            onAdd={() => addArea.mutate()}
            pending={removeArea.isPending}
            addPending={addArea.isPending}
          />
        </Section>
        <Section title="Konu ağacı" className="min-w-0 py-3 lg:px-4">
          <TopicTreePanel
            topics={topics}
            online={online}
            onSelect={setSelected}
            onTask={(t) => createTask.mutate(t)}
            taskPending={createTask.isPending}
            title={topicTitle}
            onTitle={setTopicTitle}
            onAdd={() => addTopic.mutate()}
            areaId={areaId}
            pending={addTopic.isPending}
          />
        </Section>
        <Section title="Konu ayrıntısı" className="min-w-0 py-3 lg:pl-4">
          {selected ? (
            <div className="space-y-4">
              <TopicDetailPanel
                selected={selected}
                stats={stats}
                online={online}
                onPatch={(body) => patch.mutate(body)}
                onRemove={() => confirmRemoveTopic(selected)}
              />
              <RelatedPanel entityId={selected.id} title="Kaynakları" relation="learns_from" />
            </div>
          ) : (
            <Empty>Bir konu seç — kaynakları orada bağlanır.</Empty>
          )}
          <div className="mt-6 space-y-6">
            <CoursesTab
              courses={courses}
              online={online}
              onProgress={(id, progress_pct) => patchCourse(id, progress_pct)}
              onRemove={(id) => removeCourse(id)}
            />
            <QueueTab queue={queue} online={online} onMove={(id, queue_kind) => moveQueue(id, queue_kind)} />
          </div>
        </Section>
      </div>
    </PageFrame>
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
          taskPending={taskPending}
          onTask={onTask}
          onFocus={(t) => navigate(`/pomodoro?context=${t.id}&topic=${encodeURIComponent(t.title)}`)}
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
      <Field label="Durum">
        <Select value={selected.status} disabled={!online} onChange={(v) => onPatch({ status: v })} className="w-full">
          <option value="not_started">başlamadı</option>
          <option value="in_progress">devam</option>
          <option value="done">tamam</option>
        </Select>
      </Field>
      <div>
        <p className="mb-1 text-meta text-muted">Güven</p>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <Button
              key={n}
              disabled={!online}
              variant={selected.confidence === n ? "primary" : "ghost"}
              onClick={() => onPatch({ confidence: n })}
            >
              {n}
            </Button>
          ))}
        </div>
      </div>
      <Button
        variant="primary"
        onClick={() => navigate(`/pomodoro?context=${selected.id}&title=${encodeURIComponent(selected.title)}`)}
      >
        Pomodoro başlat
      </Button>
    </div>
  );
}

function TopicTree({
  items,
  select,
  depth = 0,
  onTask,
  onFocus,
  taskPending,
}: {
  items: StudyTopic[];
  select: (t: StudyTopic) => void;
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
          <div className="group flex w-full items-center gap-1 pr-1 hover:bg-surface-hover">
            <button
              onClick={() => select(t)}
              style={{ paddingLeft: `${depth * 16 + 8}px` }}
              className="min-w-0 flex-1 py-2 text-left text-body"
            >
              <span className="block truncate">{t.title}</span>
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
              <Chip tone={t.status === "done" ? "ok" : "neutral"}>{t.confidence ? `${t.confidence}/5` : t.status}</Chip>
            </span>
          </div>
          <TopicTree
            items={t.children ?? []}
            select={select}
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
