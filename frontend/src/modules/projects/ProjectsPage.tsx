import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useHashRoute } from "@/app/router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  Field,
  IconButton,
  Input,
  PageFrame,
  PageHeader,
  Section,
  Select,
  Textarea,
  cx,
  relativeTime,
  useToast,
} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import type { Project } from "@/core/types";
import { RelatedPanel } from "@/core/RelatedPanel";
import { GithubPanel } from "./GithubPanel";
import { ProjectTodos } from "./ProjectTodos";
import { Milestones } from "./Milestones";
import { ProjectTimeline } from "./ProjectTimeline";

const STATUSES = [
  { value: "active", label: "aktif", tone: "ok", dot: "bg-ok" },
  { value: "paused", label: "beklemede", tone: "warn", dot: "bg-warn" },
  { value: "done", label: "bitti", tone: "neutral", dot: "bg-icon" },
  { value: "idea", label: "fikir", tone: "accent", dot: "bg-accent" },
] as const;

const statusOf = (value: string) => STATUSES.find((item) => item.value === value) ?? STATUSES[0];

/**
 * Proje yonetimi: solda liste, sagda secili projenin her seyi.
 *
 * Tek ekranda kalmasinin sebebi projeler arasi gecisin ucuz olmasi --
 * her proje icin ayri sayfaya gidip geri gelmek is akisini kesiyordu.
 */
export function ProjectsPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const online = useOnline();

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });

  // Ilk yuklemede ilk projeyi ac; secili proje silinirse listeye don.
  useEffect(() => {
    if (projects.length === 0) return;
    if (!selected || !projects.some((project) => project.id === selected)) {
      setSelected(projects[0].id);
    }
  }, [projects, selected]);

  const current = projects.find((project) => project.id === selected) ?? null;

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Planlama"
        title="Projeler"
        action={
          <Button variant="primary" size="sm" onClick={() => setAdding((v) => !v)} disabled={!online}>
            <Plus size={14} /> {adding ? "vazgeç" : "Yeni proje"}
          </Button>
        }
      />

      {adding && (
        <NewProject
          onDone={(id) => {
            setAdding(false);
            invalidateAfter("project.write");
            setSelected(id);
          }}
        />
      )}

      {isLoading ? (
        <p className="text-body text-muted">Yükleniyor…</p>
      ) : projects.length === 0 ? (
        <Empty variant="page" title="Henüz proje yok">
          Bir proje aç, GitHub deposunu bağla; issue'ları buradan göreve çevirirsin.
        </Empty>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-start">
          <Section title="Projeler" hint={`${projects.length}`} bodyClassName="p-0">
            <ul className="divide-y divide-subtle">
              {projects.map((project) => {
                const status = statusOf(project.status);
                const active = project.id === selected;
                return (
                  <li key={project.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(project.id)}
                      aria-current={active ? "true" : undefined}
                      className={cx(
                        "flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left transition",
                        active ? "bg-accent-surface" : "hover:bg-surface-hover",
                      )}
                    >
                      <span className={cx("mt-1.5 h-2 w-2 shrink-0 rounded-full", status.dot)} />
                      <span className="min-w-0 flex-1">
                        <span
                          className={cx(
                            "block truncate text-body",
                            active ? "font-medium text-primary" : "text-secondary",
                          )}
                        >
                          {project.title}
                        </span>
                        <span className="block truncate text-meta text-muted">
                          {project.github_repo ?? status.label}
                          {project.last_activity_at && ` · ${relativeTime(project.last_activity_at)}`}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </Section>

          {current && <ProjectDetail key={current.id} project={current} />}
        </div>
      )}
    </PageFrame>
  );
}

function ProjectDetail({ project }: { project: Project }) {
  const online = useOnline();
  const toast = useToast();

  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/projects/${project.id}`, body),
    onSuccess: () => invalidateAfter("project.write"),
    onError: () => toast.push("Kaydedilemedi.", { tone: "danger" }),
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/projects/${project.id}`),
    onSuccess: () => {
      invalidateAfter("project.write");
      toast.push("Proje silindi — bağlı görevler durmaya devam ediyor.", { tone: "ok" });
    },
  });

  const status = statusOf(project.status);

  return (
    <div className="min-w-0 space-y-5">
      <Section
        title={project.title}
        hint={<Chip tone={status.tone}>{status.label}</Chip>}
        action={
          <span className="flex items-center gap-2">
            {project.url && (
              <a
                href={project.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-meta text-accent hover:underline"
              >
                <ExternalLink size={12} /> aç
              </a>
            )}
            <IconButton
              title="Projeyi sil"
              tone="danger"
              disabled={!online || remove.isPending}
              onClick={async () => {
                const ok = await confirmDialog({
                  title: `"${project.title}" silinsin mi?`,
                  body: "Kilometre taşları da gider. Projeye bağlı görevler kalır.",
                  confirmLabel: "Sil",
                  tone: "danger",
                });
                if (ok) remove.mutate();
              }}
            >
              <Trash2 size={14} />
            </IconButton>
          </span>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Durum">
            <Select
              value={project.status}
              onChange={(value) => patch.mutate({ status: value })}
              disabled={!online}
              className="w-full"
              ariaLabel="Proje durumu"
            >
              {STATUSES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="GitHub deposu" hint="sahip/depo">
            <SavedInput
              value={project.github_repo ?? ""}
              disabled={!online}
              ariaLabel="GitHub deposu"
              placeholder="sahip/depo"
              onSave={(value) => patch.mutate({ github_repo: value || null })}
            />
          </Field>
        </div>

        <div className="mt-3">
          <Field label="Proje bağlantısı" hint="site, doküman, board…">
            <SavedInput
              value={project.url ?? ""}
              disabled={!online}
              ariaLabel="Proje bağlantısı"
              placeholder="https://…"
              onSave={(value) => patch.mutate({ url: value || null })}
            />
          </Field>
        </div>
      </Section>

      <GithubPanel project={project} />
      <Milestones project={project} />
      <ProjectTodos project={project} />

      <Section title="Notlar" hint="alandan çıkınca kaydedilir">
        <SavedTextarea
          value={project.notes ?? ""}
          disabled={!online}
          onSave={(value) => patch.mutate({ notes: value || null })}
        />
      </Section>

      <ProjectTimeline projectId={project.id} />
      <RelatedPanel entityId={project.id} title="Bağlı kayıtlar" />
    </div>
  );
}

function NewProject({ onDone }: { onDone: (id: string) => void }) {
  const [title, setTitle] = useState("");
  const [repo, setRepo] = useState("");
  const online = useOnline();
  const toast = useToast();

  const create = useMutation({
    mutationFn: () =>
      api.post<Project>("/projects", {
        title: title.trim(),
        github_repo: repo.trim() || undefined,
      }),
    onSuccess: (project) => onDone(project.id),
    onError: () => toast.push("Proje açılamadı.", { tone: "danger" }),
  });

  return (
    <Section title="Yeni proje">
      <form
        className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) create.mutate();
        }}
      >
        <Field label="Ad">
          <Input value={title} onChange={setTitle} placeholder="Proje adı" className="w-full" />
        </Field>
        <Field label="GitHub deposu" hint="isteğe bağlı">
          <Input value={repo} onChange={setRepo} placeholder="sahip/depo" className="w-full" />
        </Field>
        <Button type="submit" variant="primary" disabled={!online || !title.trim() || create.isPending}>
          Oluştur
        </Button>
      </form>
    </Section>
  );
}

/**
 * Yazarken serbest, alandan cikinca kaydeden alan.
 *
 * Her tusa basista PATCH atmak local API'de bile gereksiz gurultu; ayri bir
 * "kaydet" dugmesi ise akisi kesiyor. Deger disaridan degisirse (baska proje
 * secilince) tazelenir.
 */
function SavedInput({
  value,
  onSave,
  disabled,
  ariaLabel,
  placeholder,
}: {
  value: string;
  onSave: (value: string) => void;
  disabled?: boolean;
  ariaLabel: string;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => {
    setDraft(value);
  }, [value]);

  return (
    <Input
      value={draft}
      onChange={setDraft}
      onBlur={(next) => {
        if (next.trim() !== value) onSave(next.trim());
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
      }}
      disabled={disabled}
      placeholder={placeholder}
      ariaLabel={ariaLabel}
      className="w-full"
    />
  );
}

function SavedTextarea({
  value,
  onSave,
  disabled,
}: {
  value: string;
  onSave: (value: string) => void;
  disabled?: boolean;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => {
    setDraft(value);
  }, [value]);
  const dirty = draft.trim() !== value.trim();

  return (
    <>
      <Textarea
        value={draft}
        onChange={setDraft}
        onBlur={(next) => {
          if (next.trim() !== value) onSave(next.trim());
        }}
        rows={8}
        placeholder={
          "Karar kayıtları, açık sorular, bağlantılar…\n\n" + "Ne olduğu Günlük'te zaten duruyor; burası NEDEN'in yeri."
        }
        className={cx("font-mono text-meta leading-6", disabled && "opacity-60")}
      />
      <p className="mt-1 text-meta text-muted">
        {dirty ? "kaydedilmedi — alandan çıkınca kaydedilir" : `${draft.length} karakter`}
      </p>
    </>
  );
}
