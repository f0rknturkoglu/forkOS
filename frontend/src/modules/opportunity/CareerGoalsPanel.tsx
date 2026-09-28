import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Checkbox, Empty, Input, Select, useToast } from "@/core/ui";
import type { components } from "@/generated/api-schema";

type Goal = components["schemas"]["GoalOut"];

export function CareerGoalsPanel() {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [horizon, setHorizon] = useState<"short_term" | "quarter" | "year" | "long_term">("quarter");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [milestoneTitle, setMilestoneTitle] = useState("");
  const goals = useQuery({
    queryKey: ["career-goals"],
    queryFn: () => api.get<Goal[]>("/goals"),
  });
  const selected = useQuery({
    queryKey: ["career-goal", selectedId],
    queryFn: () => api.get<Goal>(`/goals/${selectedId}`),
    enabled: Boolean(selectedId),
  });
  const refresh = () => invalidateAfter("goal.write");
  const create = useMutation({
    mutationFn: () => api.post<Goal>("/goals", { title: title.trim(), horizon }),
    onSuccess: (goal) => {
      setTitle("");
      setSelectedId(goal.id);
      refresh();
      toast.push("Hedef oluşturuldu.", { tone: "ok" });
    },
    onError: () => toast.push("Hedef oluşturulamadı.", { tone: "danger" }),
  });
  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Goal["status"] }) => api.patch(`/goals/${id}`, { status }),
    onSuccess: refresh,
    onError: () => toast.push("Hedef durumu değiştirilemedi.", { tone: "danger" }),
  });
  const addMilestone = useMutation({
    mutationFn: () => api.post(`/goals/${selectedId}/milestones`, { title: milestoneTitle.trim() }),
    onSuccess: () => {
      setMilestoneTitle("");
      refresh();
    },
    onError: () => toast.push("Kilometre taşı eklenemedi.", { tone: "danger" }),
  });
  const toggleMilestone = useMutation({
    mutationFn: ({ id, completed }: { id: string; completed: boolean }) =>
      api.patch(`/goal-milestones/${id}`, { completed }),
    onSuccess: refresh,
    onError: () => toast.push("Kilometre taşı güncellenemedi.", { tone: "danger" }),
  });

  const activeGoal = selected.data ?? goals.data?.find((goal) => goal.id === selectedId);
  return (
    <div className="space-y-3 border-t border-subtle pt-4">
      <h3 className="text-body font-semibold text-primary">Operasyonel hedefler</h3>
      <p className="text-meta text-muted">
        Semantik hedeflerden ayrı, ölçülebilir kayıtlar. Oluşturma ve tamamlama yalnızca senin işleminle olur.
      </p>
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) create.mutate();
        }}
      >
        <Input
          value={title}
          onChange={setTitle}
          ariaLabel="Yeni hedef başlığı"
          placeholder="Yeni ölçülebilir hedef"
          className="min-w-[180px] flex-1"
        />
        <Select value={horizon} onChange={(value) => setHorizon(value as typeof horizon)} ariaLabel="Hedef ufku">
          <option value="short_term">Kısa vade</option>
          <option value="quarter">Çeyrek</option>
          <option value="year">Yıl</option>
          <option value="long_term">Uzun vade</option>
        </Select>
        <Button type="submit" size="sm" disabled={!title.trim() || create.isPending}>
          Hedef ekle
        </Button>
      </form>
      {goals.isError && (
        <p role="alert" className="text-meta text-danger">
          Hedefler yüklenemedi.
        </p>
      )}
      {goals.data?.length === 0 && (
        <Empty title="Operasyonel hedef yok">Öneriden onaylayabilir veya burada açıkça oluşturabilirsin.</Empty>
      )}
      <div className="flex flex-wrap gap-2">
        {goals.data?.map((goal) => (
          <Button
            key={goal.id}
            size="sm"
            variant={goal.id === selectedId ? "primary" : "ghost"}
            onClick={() => setSelectedId(goal.id)}
          >
            {goal.title} · {goal.progress_percent === null ? "ölçüt yok" : `%${goal.progress_percent}`}
          </Button>
        ))}
      </div>
      {activeGoal && (
        <div className="space-y-3 rounded-card border border-subtle bg-surface p-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="min-w-0 flex-1 text-body text-primary">
              {activeGoal.title}: {activeGoal.completed_milestones}/{activeGoal.milestone_count} kilometre taşı
            </p>
            <Select
              value={activeGoal.status}
              onChange={(value) => update.mutate({ id: activeGoal.id, status: value as Goal["status"] })}
              ariaLabel={`${activeGoal.title} durumu`}
            >
              <option value="active">Aktif</option>
              <option value="paused">Duraklatıldı</option>
              <option value="completed">Tamamlandı</option>
              <option value="retired">Emekli</option>
            </Select>
          </div>
          <form
            className="flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (milestoneTitle.trim()) addMilestone.mutate();
            }}
          >
            <Input
              value={milestoneTitle}
              onChange={setMilestoneTitle}
              ariaLabel="Yeni hedef kilometre taşı"
              placeholder="Ölçülebilir kilometre taşı"
              className="min-w-0 flex-1"
            />
            <Button type="submit" size="sm" disabled={!milestoneTitle.trim() || addMilestone.isPending}>
              Ekle
            </Button>
          </form>
          {activeGoal.milestones.map((milestone) => (
            <Checkbox
              key={milestone.id}
              checked={Boolean(milestone.completed_at)}
              onChange={(completed) => toggleMilestone.mutate({ id: milestone.id, completed })}
              label={milestone.title}
            />
          ))}
        </div>
      )}
    </div>
  );
}
