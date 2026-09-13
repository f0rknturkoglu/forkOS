import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, Link2, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, Field, IconButton, Input, Section, Select, Textarea, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { ApplicationListPage, CareerStory, CareerStoryProvenance, CoverLetter, Opportunity } from "@/core/types";
import { PROVENANCE_LABELS, storyOverlapsText, storySearchText } from "./careerUtils";

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

const STORY_FIELDS = [
  ["situation", "S · Durum"],
  ["task", "T · Görev"],
  ["action", "A · Eylem"],
  ["result", "R · Sonuç"],
  ["reflection", "R · Çıkarım"],
] as const;

function ApplicationUsage({ story }: { story: CareerStory }) {
  const storyId = story.id;
  // Aynı sorgu anahtarı diğer panellerle paylaşılır: tek istek, tek önbellek.
  const { data: applicationsPage } = useQuery({
    queryKey: ["applications"],
    queryFn: () => api.get<ApplicationListPage>("/applications?limit=200"),
  });
  const applications = applicationsPage?.items ?? [];
  const covers = useQuery({
    queryKey: ["career-cover-letters"],
    // Kayıt başına istek YOK: kaydedilmiş ön yazılar tek uçtan gelir.
    queryFn: async () => {
      return api.get<CoverLetter[]>("/career/cover-letters");
    },
  });

  const usedIn = applications
    .map((item) => ({
      item,
      requirements: (item.evaluation?.matches ?? [])
        .filter((match) => match.story_ids.includes(storyId))
        .map((match) => match.requirement),
    }))
    .filter((entry) => entry.requirements.length > 0);
  const skills = [...new Set(usedIn.flatMap((entry) => entry.requirements))];
  const letters = (covers.data ?? []).filter((row) => storyOverlapsText(story, row.cover_letter));

  return (
    <div className="space-y-3 rounded-card border border-subtle bg-surface p-3">
      <div>
        <span className="text-meta font-medium text-secondary">Kullanıldığı başvurular</span>
        {usedIn.length === 0 ? (
          <p className="mt-1 text-meta text-muted">Bu hikâye henüz bir başvurunun gereksinim eşleşmesinde geçmiyor.</p>
        ) : (
          <ul className="mt-1 space-y-1">
            {usedIn.map(({ item, requirements }) => (
              <li key={item.id} className="text-meta text-secondary">
                <span className="text-primary">{item.title}</span>
                {item.organization ? ` · ${item.organization}` : ""} — {requirements.join(", ")}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <span className="text-meta font-medium text-secondary">İlgili beceriler</span>
        <div className="mt-1 flex flex-wrap gap-1">
          {skills.length === 0 ? (
            <span className="text-meta text-muted">Eşleşmiş gereksinim yok.</span>
          ) : (
            skills.map((skill) => <Chip key={skill}>{skill}</Chip>)
          )}
        </div>
      </div>
      <div>
        <span className="text-meta font-medium text-secondary">Metni bu hikâyele örtüşen ön yazılar</span>
        {covers.isLoading ? (
          <p className="mt-1 text-meta text-muted">Yerel ön yazılar taranıyor…</p>
        ) : covers.isError ? (
          <p role="alert" className="mt-1 text-meta text-danger">
            Ön yazılar yüklenemedi: {covers.error instanceof Error ? covers.error.message : "bilinmeyen hata"}
          </p>
        ) : letters.length === 0 ? (
          <p className="mt-1 text-meta text-muted">Örtüşen ön yazı bulunmadı (yerel kelime taraması).</p>
        ) : (
          <ul className="mt-1 space-y-1">
            {letters.map((letter) => (
              <li key={letter.opportunity_id} className="text-meta text-secondary">
                <span className="text-primary">{letter.title}</span>
                {letter.organization ? ` · ${letter.organization}` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function CareerStoryBank({ focusId }: { focusId?: string | null }) {
  const online = useOnline();
  const [selectedId, setSelectedId] = useState<string | null>(focusId ?? null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [search, setSearch] = useState("");
  const [provenanceFilter, setProvenanceFilter] = useState<"" | CareerStoryProvenance>("");
  const {
    data: stories = [],
    isError: storiesFailed,
    error: storiesError,
    isFetching: storiesFetching,
    refetch: refetchStories,
  } = useQuery({
    queryKey: ["career-stories"],
    queryFn: () => api.get<CareerStory[]>("/career/stories"),
  });
  const selected = stories.find((story) => story.id === selectedId) ?? null;
  const editorOpen = creating || selected !== null;

  useEffect(() => {
    if (!focusId) return;
    setCreating(false);
    setSelectedId(focusId);
  }, [focusId]);

  useEffect(() => {
    if (!selected) return;
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
  }, [selected]);

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return stories.filter(
      (story) =>
        (!provenanceFilter || story.provenance === provenanceFilter) &&
        (!needle || storySearchText(story).includes(needle)),
    );
  }, [stories, search, provenanceFilter]);

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
      setCreating(false);
      setSelectedId(story.id);
      invalidateAfter("career.write");
    },
  });
  const archive = useMutation({
    mutationFn: (id: string) => api.del(`/career/stories/${id}`),
    onSuccess: () => {
      setSelectedId(null);
      setCreating(false);
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

  function startNew() {
    setSelectedId(null);
    setCreating(true);
    setDraft(EMPTY_DRAFT);
  }

  return (
    <Section
      title="STAR+R hikâye bankası"
      hint={storiesFailed ? "okunamadı" : `${stories.length} hikâye · tamamı yerel`}
      action={
        <Button size="sm" onClick={startNew}>
          <Plus size={13} /> Yeni hikâye
        </Button>
      }
    >
      <div className="mb-3 grid gap-2 md:grid-cols-[minmax(0,1fr)_12rem]">
        <Input
          value={search}
          onChange={setSearch}
          placeholder="Hikâye, etiket veya içerikte ara…"
          ariaLabel="Hikâyelerde ara"
          className="w-full"
        />
        <Select
          value={provenanceFilter}
          onChange={(value) => setProvenanceFilter(value as "" | CareerStoryProvenance)}
          ariaLabel="Kaynak filtresi"
          className="w-full"
        >
          <option value="">Tüm kaynaklar</option>
          {Object.entries(PROVENANCE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      <div className={cx("grid gap-4", editorOpen ? "lg:grid-cols-2" : "")}>
        <div className="space-y-2">
          {storiesFailed ? (
            <div
              role="alert"
              className="space-y-2 rounded-control border border-danger-border bg-danger-surface px-3 py-3"
            >
              <p className="text-meta text-danger">
                Hikâyeler yüklenemedi: {storiesError instanceof Error ? storiesError.message : "bilinmeyen hata"}
              </p>
              <Button size="sm" disabled={storiesFetching} onClick={() => void refetchStories()}>
                Tekrar dene
              </Button>
            </div>
          ) : visible.length === 0 ? (
            <Empty title={stories.length === 0 ? "Hikâye bankası henüz boş" : "Bu filtreye uyan hikâye yok"}>
              {stories.length === 0
                ? "Mülakatta tekrar kullanacağın ilk somut hikâyeyi “Yeni hikâye” ile ekle."
                : "Arama ya da kaynak filtresini gevşetebilirsin."}
            </Empty>
          ) : (
            visible.map((story) => (
              <button
                key={story.id}
                type="button"
                onClick={() => {
                  setCreating(false);
                  setSelectedId(story.id);
                }}
                className={cx(
                  "w-full rounded-control border p-3 text-left transition",
                  selectedId === story.id && !creating
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

        {editorOpen && (
          <div className="space-y-3 rounded-card border border-subtle bg-surface-sunken p-4">
            <div className="flex items-center gap-2">
              <Input
                value={draft.title}
                onChange={(title) => setDraft((current) => ({ ...current, title }))}
                placeholder="Hikâye başlığı"
                ariaLabel="Hikâye başlığı"
                className="min-w-0 flex-1"
              />
              {selected && (
                <IconButton title="Hikâyeyi arşivle" tone="danger" disabled={!online} onClick={removeSelected}>
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
            {STORY_FIELDS.map(([key, label]) => (
              <Textarea
                key={key}
                value={draft[key]}
                onChange={(value) => setDraft((current) => ({ ...current, [key]: value }))}
                rows={2}
                placeholder={label}
                ariaLabel={label}
              />
            ))}
            <Field label="Etiketler (virgülle)">
              <Input
                value={draft.tags}
                onChange={(tags) => setDraft((current) => ({ ...current, tags }))}
                placeholder="liderlik, ölçekleme, veri"
                className="w-full"
              />
            </Field>
            <div className="flex items-center justify-between gap-2">
              <Button
                variant="primary"
                disabled={!online || !draft.title.trim() || save.isPending}
                title={online ? undefined : "Çevrimdışısın: yazma kapalı"}
                onClick={() => save.mutate()}
              >
                {selected ? "Hikâyeyi güncelle" : "Hikâyeyi kaydet"}
              </Button>
              <Button
                onClick={() => {
                  setCreating(false);
                  setSelectedId(null);
                }}
              >
                Kapat
              </Button>
            </div>
            {!online && (
              <p role="status" className="text-meta text-warn">
                Çevrimdışısın: hikâye kaydedilemez veya arşivlenemez.
              </p>
            )}
            {selected && (
              <div className="border-t border-subtle pt-3">
                <span className="mb-2 flex items-center gap-1 text-meta font-medium text-secondary">
                  <Link2 size={13} /> Kullanım izleri
                </span>
                <ApplicationUsage story={selected} />
              </div>
            )}
          </div>
        )}
      </div>
      {!editorOpen && stories.length > 0 && (
        <p className="mt-3 flex items-center gap-1 text-meta text-muted">
          <BookOpen size={13} /> Düzenlemek için bir hikâye seç, yenisi için “Yeni hikâye”.
        </p>
      )}
    </Section>
  );
}
