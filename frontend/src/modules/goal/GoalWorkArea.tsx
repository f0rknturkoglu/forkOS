import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, Check, ExternalLink, ListTodo, Plus } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { entityRoute, typeLabel } from "@/core/entityRegistry";
import { planDayForToday } from "@/core/tasks";
import { Button, Checkbox, Empty, Field, Input, Modal, Select, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";

type S = components["schemas"];
type Action = S["WorkAction"];
type Request = S["GoalActionIn"];

export function GoalWorkArea({ objective }: { objective: S["ObjectiveState"] }) {
  const online = useOnline();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [learningStep, setLearningStep] = useState<string | null>(null);
  const [area, setArea] = useState("");
  const [areaTitle, setAreaTitle] = useState("");
  const identities = useRef(new Map<string, string>());
  const work = objective.work;
  const allActions = work?.actions ?? [];
  const goal = objective.goal;
  const areas = useQuery({
    queryKey: ["study-areas"],
    queryFn: () => api.get<S["StudyAreaOut"][]>("/study/areas"),
    enabled: learningStep !== null,
  });
  const write = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => invalidateAfter("goal.write", "todo.write"),
    onError: (error: Error) => toast.push(error.message || "Kaydedilemedi.", { tone: "danger" }),
  });
  const convert = useMutation({
    mutationFn: (body: Request) => api.post<S["GoalActionOut"]>(`/goals/${goal.id}/actions`, body),
    onSuccess: (item) => {
      invalidateAfter("goal-action.write");
      setLearningStep(null);
      toast.push(item.type === "todo" ? "Görevlere eklendi." : "Öğrenmeye eklendi.", { tone: "ok" });
    },
    onError: (error: Error) => toast.push(error.message || "Eklenemedi. Yeniden deneyebilirsin.", { tone: "danger" }),
  });
  const addAction = (milestoneId: string, kind: "todo" | "study_topic") => {
    if (!online || convert.isPending) return;
    const key = [milestoneId, kind, area, areaTitle].join(":");
    const identity = identities.current.get(key) ?? crypto.randomUUID();
    identities.current.set(key, identity);
    convert.mutate({
      client_uuid: identity,
      milestone_id: milestoneId,
      kind,
      ...(kind === "todo"
        ? { plan_day: planDayForToday() }
        : area === "new"
          ? { new_area_title: areaTitle.trim() }
          : { area_id: area }),
    });
  };
  return (
    <div className="stack-y-4">
      <div data-onboarding="goal-milestone" className="flex items-center justify-between gap-3">
        <h2 className="text-heading">Sıradaki adımlar</h2>
        <Button size="sm" onClick={() => setAdding(!adding)} ariaExpanded={adding} disabled={!online}>
          <Plus size={14} /> Adım ekle
        </Button>
      </div>
      {adding && (
        <form
          className="flex gap-2"
          data-onboarding="goal-milestone"
          onSubmit={(event) => {
            event.preventDefault();
            if (!online || write.isPending || !title.trim()) return;
            write.mutate(() =>
              api.post(`/goals/${goal.id}/milestones`, { title: title.trim() }).then(() => {
                setTitle("");
                setAdding(false);
              }),
            );
          }}
        >
          <Input
            ariaLabel="Yeni hedef adımı"
            value={title}
            onChange={setTitle}
            placeholder="Küçük ve yapılabilir bir adım…"
            className="min-w-0 flex-1"
          />
          <Button type="submit" disabled={!online || !title.trim() || write.isPending}>
            Ekle
          </Button>
        </form>
      )}
      {!goal.milestones.length && <Empty>Hedefini küçük adımlara ayırarak başlayabilirsin.</Empty>}
      <div className="stack-y-3">
        {goal.milestones.map((step) => {
          const state = work?.milestones?.find((m) => m.id === step.id);
          const actions = allActions.filter((a) => (a.milestone_ids ?? []).includes(step.id)) ?? [];
          const completed = state?.completed ?? Boolean(step.completed_at);
          const derived = completed && !state?.manual_completed && actions.length > 0;
          return (
            <section key={step.id} className="rounded-card border border-subtle p-4 stack-y-3">
              <div className="flex items-start justify-between gap-3">
                <Checkbox
                  label={step.title}
                  checked={completed}
                  disabled={!online || write.isPending || derived}
                  onChange={(checked) =>
                    write.mutate(() => api.patch(`/goal-milestones/${step.id}`, { completed: checked }))
                  }
                />
                {completed && (
                  <span className="flex shrink-0 items-center gap-1 text-meta text-ok">
                    <Check size={12} /> Tamamlandı
                  </span>
                )}
              </div>
              {actions.map((action) => (
                <ActionRow
                  key={action.id}
                  action={action}
                  busy={write.isPending}
                  onToggle={(checked) =>
                    write.mutate(() => api.patch(`/todos/${action.id}`, { status: checked ? "done" : "open" }))
                  }
                />
              ))}
              {!completed && (
                <div className="flex flex-wrap gap-2">
                  {!actions.some((a) => a.type === "todo") && (
                    <Button
                      size="sm"
                      ariaLabel={`${step.title}: Göreve ekle`}
                      disabled={!online || convert.isPending}
                      onClick={() => addAction(step.id, "todo")}
                    >
                      <ListTodo size={14} /> Göreve ekle
                    </Button>
                  )}
                  {!actions.some((a) => a.type === "study_topic") && (
                    <Button
                      size="sm"
                      ariaLabel={`${step.title}: Öğrenmeye ekle`}
                      disabled={!online || convert.isPending}
                      onClick={() => {
                        setArea("");
                        setAreaTitle("");
                        setLearningStep(step.id);
                      }}
                    >
                      <BookOpen size={14} /> Öğrenmeye ekle
                    </Button>
                  )}
                </div>
              )}
            </section>
          );
        })}
      </div>
      {(allActions.filter((a) => !(a.milestone_ids ?? []).length).length ?? 0) > 0 && (
        <section className="stack-y-3">
          <h2 className="text-heading">Diğer çalışmalar</h2>
          {allActions
            .filter((a) => !(a.milestone_ids ?? []).length)
            .map((action) => (
              <ActionRow
                key={action.id}
                action={action}
                busy={write.isPending}
                onToggle={(checked) =>
                  write.mutate(() => api.patch(`/todos/${action.id}`, { status: checked ? "done" : "open" }))
                }
              />
            ))}
        </section>
      )}
      <Modal open={learningStep !== null} onClose={() => setLearningStep(null)} title="Öğrenmeye ekle">
        <form
          className="stack-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (learningStep) addAction(learningStep, "study_topic");
          }}
        >
          <p className="text-body">{goal.milestones.find((step) => step.id === learningStep)?.title}</p>
          {areas.isError ? (
            <div role="alert">
              Öğrenme alanları alınamadı. <Button onClick={() => void areas.refetch()}>Yeniden dene</Button>
            </div>
          ) : (
            <Field label="Hangi alanda çalışacaksın?">
              <Select
                ariaLabel="Öğrenme alanı"
                value={area}
                onChange={setArea}
                disabled={areas.isPending || convert.isPending}
              >
                <option value="">Alan seç</option>
                {areas.data?.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
                <option value="new">Yeni alan oluştur</option>
              </Select>
            </Field>
          )}
          {area === "new" && (
            <Field label="Yeni alanın adı">
              <Input
                ariaLabel="Yeni alanın adı"
                value={areaTitle}
                onChange={setAreaTitle}
                placeholder="Örn. İngilizce"
                disabled={convert.isPending}
              />
            </Field>
          )}
          <Button
            type="submit"
            variant="primary"
            disabled={!online || convert.isPending || areas.isError || !area || (area === "new" && !areaTitle.trim())}
          >
            Öğrenmeye ekle
          </Button>
        </form>
      </Modal>
    </div>
  );
}

function ActionRow({
  action,
  busy,
  onToggle,
}: {
  action: Action;
  busy: boolean;
  onToggle: (checked: boolean) => void;
}) {
  const online = useOnline();
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-control bg-surface-sunken px-3 py-2">
      {action.type === "todo" ? (
        <Checkbox
          label={`${typeLabel(action.type)}: ${action.title}`}
          checked={action.completed}
          disabled={!online || busy}
          onChange={onToggle}
        />
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <BookOpen size={14} />
          <span className="text-body">{action.title}</span>
          {action.completed && <Check size={14} className="text-ok" />}
        </div>
      )}
      <a
        href={`#${entityRoute(action.type, action.id).replace(/^#/, "")}`}
        className="ml-auto shrink-0 inline-flex items-center gap-1 text-meta text-secondary hover:text-accent"
      >
        <ExternalLink size={12} />
        {action.type === "todo" ? "Görevde aç" : "Öğrenmede aç"}
      </a>
    </div>
  );
}
