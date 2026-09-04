import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, IconButton, Input, Section, Select, Textarea, cx } from "@/core/ui";
import type { CareerStory, CareerStoryProvenance } from "@/core/types";

const PROVENANCE_LABELS: Record<CareerStoryProvenance, string> = {
  existing: "Doğrudan yaşandı",
  supported: "Belgeyle destekli",
  "derived-unverified": "Türetilmiş · doğrulanmadı",
  "user-cannot-confirm": "Doğrulanamıyor",
};

const EMPTY_DRAFT = {
  title: "",
  situation: "",
  task: "",
  action: "",
  result: "",
  reflection: "",
  provenance: "existing" as CareerStoryProvenance,
  tags: "",
};

export function CareerStoryBank({ focusId }: { focusId?: string | null }) {
  const [selectedId, setSelectedId] = useState<string | null>(focusId ?? null);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const { data: stories = [] } = useQuery({
    queryKey: ["career-stories"],
    queryFn: () => api.get<CareerStory[]>("/career/stories"),
  });
  const selected = stories.find((story) => story.id === selectedId) ?? null;

  useEffect(() => {
    if (!selected) {
      if (!selectedId) setDraft(EMPTY_DRAFT);
      return;
    }
    setDraft({
      title: selected.title,
      situation: selected.situation ?? "",
      task: selected.task ?? "",
      action: selected.action ?? "",
      result: selected.result ?? "",
      reflection: selected.reflection ?? "",
      provenance: selected.provenance,
      tags: selected.tags.join(", "),
    });
  }, [selected, selectedId]);

  const payload = () => ({
    ...draft,
    tags: draft.tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
  });
  const save = useMutation({
    mutationFn: () =>
      selectedId
        ? api.patch<CareerStory>(`/career/stories/${selectedId}`, payload())
        : api.post<CareerStory>("/career/stories", payload()),
    onSuccess: (story) => {
      setSelectedId(story.id);
      invalidateAfter("career.write");
    },
  });
  const archive = useMutation({
    mutationFn: (id: string) => api.del(`/career/stories/${id}`),
    onSuccess: () => {
      setSelectedId(null);
      setDraft(EMPTY_DRAFT);
      invalidateAfter("career.write");
    },
  });

  async function removeSelected() {
    if (!selected) return;
    const ok = await confirmDialog({
      title: "Hikâye arşivlensin mi?",
      body: selected.title,
      confirmLabel: "Arşivle",
      tone: "danger",
    });
    if (ok) archive.mutate(selected.id);
  }

  return (
    <Section
      title="STAR+R hikâye bankası"
      hint={`${stories.length} hikâye · tamamı yerel`}
      action={
        <Button
          size="sm"
          onClick={() => {
            setSelectedId(null);
            setDraft(EMPTY_DRAFT);
          }}
        >
          <Plus size={13} /> Yeni hikâye
        </Button>
      }
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          {stories.length === 0 ? (
            <div className="rounded-control border border-dashed border-strong p-5 text-center text-meta text-muted">
              <BookOpen size={18} className="mx-auto mb-2" />
              Mülakatta tekrar kullanacağın ilk somut hikâyeyi ekle.
            </div>
          ) : (
            stories.map((story) => (
              <button
                key={story.id}
                type="button"
                onClick={() => setSelectedId(story.id)}
                className={cx(
                  "w-full rounded-control border p-3 text-left transition",
                  selectedId === story.id
                    ? "border-accent-border bg-accent-surface"
                    : "border-subtle bg-surface hover:bg-surface-hover",
                )}
              >
                <strong className="block text-body text-primary">{story.title}</strong>
                <span className="mt-1 flex flex-wrap gap-1">
                  <Chip>{PROVENANCE_LABELS[story.provenance]}</Chip>
                  {story.tags.slice(0, 3).map((tag) => (
                    <Chip key={tag}>{tag}</Chip>
                  ))}
                </span>
              </button>
            ))
          )}
        </div>

        <div className="space-y-3 rounded-card border border-subtle bg-surface-sunken p-4">
          <div className="flex items-center gap-2">
            <Input
              value={draft.title}
              onChange={(title) => setDraft((current) => ({ ...current, title }))}
              placeholder="Hikâye başlığı"
              className="min-w-0 flex-1"
            />
            {selected && (
              <IconButton title="Hikâyeyi arşivle" tone="danger" onClick={removeSelected}>
                <Trash2 size={14} />
              </IconButton>
            )}
          </div>
          <Select
            value={draft.provenance}
            onChange={(provenance) =>
              setDraft((current) => ({ ...current, provenance: provenance as CareerStoryProvenance }))
            }
            ariaLabel="İddia kaynağı"
            className="w-full"
          >
            {Object.entries(PROVENANCE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          {(
            [
              ["situation", "S · Durum"],
              ["task", "T · Görev"],
              ["action", "A · Eylem"],
              ["result", "R · Sonuç"],
              ["reflection", "R · Çıkarım"],
            ] as const
          ).map(([key, label]) => (
            <Textarea
              key={key}
              value={draft[key]}
              onChange={(value) => setDraft((current) => ({ ...current, [key]: value }))}
              rows={2}
              placeholder={label}
              ariaLabel={label}
            />
          ))}
          <Input
            value={draft.tags}
            onChange={(tags) => setDraft((current) => ({ ...current, tags }))}
            placeholder="Etiketler (virgülle)"
            className="w-full"
          />
          <Button variant="primary" disabled={!draft.title.trim() || save.isPending} onClick={() => save.mutate()}>
            {selected ? "Hikâyeyi güncelle" : "Hikâyeyi kaydet"}
          </Button>
        </div>
      </div>
    </Section>
  );
}
