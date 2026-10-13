import { invalidateAfter } from "@/core/invalidation";
import { ContextualHelp } from "@/core/ContextualHelp";
import { useEffect, useState } from "react";
import { navigate, useHashRoute } from "@/app/router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ChevronDown, ExternalLink, Github, Settings, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  Field,
  Disclosure,
  Select,
  IconButton,
  Input,
  PageFrame,
  Modal,
  Section,
  cx,
  useToast,
  SkeletonRows,
} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import type { GithubRepoPanel, Project } from "@/core/types";
import { ProjectResources, ProjectConnections } from "./ProjectResources";
import { GithubPanel } from "./GithubPanel";
import { ProjectTodos } from "./ProjectTodos";
import { Milestones } from "./Milestones";
import { MilestoneTimeline } from "./MilestoneTimeline";
import { ProjectActivityTimeline } from "./ProjectActivityTimeline";
import { ProjectJournalBridge } from "./ProjectJournalBridge";
import { ProjectKnowledgeNote } from "./ProjectKnowledgeNote";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea, WorkspaceToolbar } from "@/core/workspace/Workspace";

const STATUSES = [
  { value: "active", label: "aktif", tone: "ok", dot: "bg-ok" },
  { value: "paused", label: "beklemede", tone: "warn", dot: "bg-warn" },
  { value: "done", label: "bitti", tone: "neutral", dot: "bg-icon" },
  { value: "idea", label: "fikir", tone: "accent", dot: "bg-accent" },
] as const;

const statusOf = (value: string) => STATUSES.find((item) => item.value === value) ?? STATUSES[0];
/** Proje seçimi, aktif iş ve ikincil bağlam aynı çalışma alanında kalır. */
export function ProjectsPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus") ?? "";
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const online = useOnline();

  const {
    data: projects = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });

  // Ilk yuklemede ilk projeyi ac; secili proje silinirse listeye don.
  // Deep-link: ?focus={id} secili projeyi acar (registry rotasi, Faz 32).
  useEffect(() => {
    if (projects.length === 0) return;
    if (focusId && projects.some((project) => project.id === focusId)) {
      setSelected(focusId);
      return;
    }
    const milestoneOwner =
      focusId && projects.find((project) => project.milestones.some((item) => item.id === focusId));
    if (milestoneOwner) {
      setSelected(milestoneOwner.id);
      return;
    }
    if (focusId) {
      navigate(`/projects?focus=${encodeURIComponent(projects[0].id)}`, { replace: true });
    }
    setSelected((previous) =>
      previous && projects.some((project) => project.id === previous) ? previous : projects[0].id,
    );
  }, [projects, focusId]);

  const current = projects.find((project) => project.id === selected) ?? null;
  const selectProject = (id: string) => {
    setSelected(id);
    setSettingsOpen(false);
    navigate(`/projects?focus=${encodeURIComponent(id)}`, { replace: true });
  };

  return (
    <PageFrame className="py-3">
      {isLoading ? (
        <SkeletonRows rows={6} />
      ) : isError ? (
        <div role="alert" className="stack-y-3">
          <p className="text-body text-danger">Projeler alınamadı.</p>
          <Button onClick={() => void refetch()}>Yeniden dene</Button>
        </div>
      ) : projects.length === 0 ? (
        <div data-onboarding="project-create" className="stack-y-4">
          <Empty
            variant="page"
            title="Henüz proje yok"
            action={
              <Button variant="primary" onClick={() => setAdding(true)} disabled={!online}>
                <Plus size={14} /> Yeni proje
              </Button>
            }
          >
            Bir proje aç, GitHub deposunu bağla; issue'ları buradan göreve çevirirsin.
          </Empty>
          <Modal open={adding} onClose={() => setAdding(false)} title="Yeni proje">
            <NewProject
              onDone={(id) => {
                setAdding(false);
                selectProject(id);
              }}
            />
          </Modal>
        </div>
      ) : current ? (
        <Workspace>
          <WorkspacePaneHeader
            title={<ProjectTitle key={current.id} project={current} />}
            hint={<ProjectStatus key={current.id} project={current} />}
          />
          <WorkspaceToolbar
            left={
              <Select ariaLabel="Proje seç" value={current.id} onChange={selectProject} className="max-w-full sm:w-64">
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </Select>
            }
            right={
              <>
                <ProjectLinks project={current} />
                <Button size="sm" ariaLabel="Proje ayarları" onClick={() => setSettingsOpen(true)}>
                  <Settings size={14} /> <span className="hidden sm:inline">Ayarlar</span>
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  ariaLabel="Yeni proje"
                  onClick={() => setAdding(true)}
                  disabled={!online}
                >
                  <Plus size={14} /> <span className="hidden sm:inline">Yeni proje</span>
                </Button>
              </>
            }
          />
          <WorkspaceScrollArea className="p-4">
            <div data-onboarding="project-create" id="project-view" className="mx-auto max-w-4xl stack-y-4">
              {current.execution_progress && (
                <p className="text-meta text-secondary">
                  Çalışma ilerlemesi:{" "}
                  {current.execution_progress.percent == null
                    ? "Henüz hesaplanamıyor"
                    : `%${current.execution_progress.percent}`}{" "}
                  · {current.execution_progress.completed}/{current.execution_progress.total} iş birimi tamamlandı
                </p>
              )}
              <ContextualHelp
                key={current.id}
                context={{ kind: "project", entity_id: current.id }}
                label="Proje özeti"
              />
              <ProjectViewContent key={current.id} project={current} />
            </div>
          </WorkspaceScrollArea>
          <Modal open={adding} onClose={() => setAdding(false)} title="Yeni proje">
            <NewProject
              onDone={(id) => {
                setAdding(false);
                selectProject(id);
              }}
            />
          </Modal>
          <Modal open={settingsOpen} onClose={() => setSettingsOpen(false)} title="Proje ayarları">
            <ProjectSettings key={current.id} project={current} />
          </Modal>
        </Workspace>
      ) : null}
    </PageFrame>
  );
}

function ProjectViewContent({ project }: { project: Project }) {
  const nextMilestone = project.milestones.find((item) => !item.completed_at);
  return (
    <>
      <Section title="Sıradaki adım">
        <p className="text-body text-primary">
          {project.next_action || nextMilestone?.title || "Henüz bir sonraki adım belirlenmedi."}
        </p>
      </Section>
      <div className="grid gap-4 lg:grid-cols-2">
        <ProjectTodos project={project} />
        <Milestones project={project} />
      </div>
      <MilestoneTimeline project={project} />
      <GithubPanel project={project} />
      <div className="grid gap-4 lg:grid-cols-2">
        <ProjectKnowledgeNote project={project} />
        <ProjectJournalBridge projectId={project.id} />
      </div>
      <ProjectConnections project={project} />
      <Disclosure summary="Geçmiş" className="rounded-card border border-subtle p-3">
        <ProjectActivityTimeline projectId={project.id} />
      </Disclosure>
    </>
  );
}

function useProjectPatch(project: Project, onSaved?: () => void) {
  const toast = useToast();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/projects/${project.id}`, body),
    onSuccess: () => {
      invalidateAfter("project.write");
      onSaved?.();
    },
    onError: () => toast.push("Kaydedilemedi.", { tone: "danger" }),
  });
}

function ProjectTitle({ project }: { project: Project }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(project.title);
  const patch = useProjectPatch(project, () => setEditing(false));
  const online = useOnline();
  return editing ? (
    <form
      className="flex items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (!online || patch.isPending || !title.trim()) return;
        if (title.trim() !== project.title) patch.mutate({ title: title.trim() });
        else setEditing(false);
      }}
    >
      <Input
        autoFocus
        ariaLabel="Proje adı"
        value={title}
        onChange={setTitle}
        onKeyDown={(event) => {
          if (event.key === "Escape") setEditing(false);
        }}
        className="min-w-0 flex-1"
      />
      <Button size="sm" ariaLabel="Proje adını kaydet" type="submit" disabled={!title.trim() || patch.isPending}>
        <Check size={14} />
      </Button>
    </form>
  ) : (
    <button
      type="button"
      disabled={!online}
      aria-label="Proje adını düzenle"
      onClick={() => {
        setTitle(project.title);
        setEditing(true);
      }}
      className="max-w-full truncate text-left hover:text-accent"
    >
      {project.title}
    </button>
  );
}

function ProjectStatus({ project }: { project: Project }) {
  const [open, setOpen] = useState(false);
  const patch = useProjectPatch(project);
  const online = useOnline();
  return (
    <>
      <button type="button" aria-label="Proje durumunu değiştir" disabled={!online} onClick={() => setOpen(true)}>
        <Chip tone={statusOf(project.status).tone}>
          {statusOf(project.status).label} <ChevronDown size={12} />
        </Chip>
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Proje durumu">
        <div className="grid gap-2">
          {STATUSES.map((status) => (
            <Button
              key={status.value}
              disabled={patch.isPending || !online}
              onClick={() => {
                patch.mutate({ status: status.value });
                setOpen(false);
              }}
            >
              <span className={cx("h-2 w-2 rounded-full", status.dot)} />
              {status.label}
              {project.status === status.value && <Check size={14} />}
            </Button>
          ))}
        </div>
      </Modal>
    </>
  );
}

function GithubConnection({ project }: { project: Project }) {
  const query = useQuery({
    queryKey: ["project-github", project.id],
    queryFn: () => api.get<GithubRepoPanel>(`/projects/${project.id}/github`),
    enabled: Boolean(project.github_repo),
    staleTime: 5 * 60_000,
    retry: false,
  });
  if (!project.github_repo) return null;
  const fetched = query.data ? Date.parse(query.data.fetched_at) : NaN;
  const stale = !Number.isFinite(fetched) || Date.now() - fetched >= 3 * 86_400_000;
  const label = query.isError
    ? "Bağlantı hatası"
    : !query.data
      ? "Kontrol ediliyor"
      : stale
        ? "Yenileme bekliyor"
        : "Bağlı";
  return (
    <Chip tone={query.isError ? "danger" : stale || !query.data ? "warn" : "ok"} icon={<Github size={12} />}>
      {label}
    </Chip>
  );
}

function ProjectLinks({ project }: { project: Project }) {
  const [open, setOpen] = useState(false);
  const website = project.url && (/^https?:\/\//i.test(project.url) ? project.url : `https://${project.url}`);
  const repo = project.github_repo ? `https://github.com/${project.github_repo}` : null;
  if (!website && !repo) return null;
  const links = [
    { label: "Proje bağlantısı", url: website },
    { label: "GitHub deposu", url: repo },
  ].filter((link) => link.url);
  const linkClass =
    "inline-flex h-8 items-center justify-center gap-1.5 rounded-control border border-subtle px-3 text-meta text-secondary transition hover:bg-surface-hover hover:text-primary";
  return (
    <>
      {links.length === 1 ? (
        <a className={linkClass} href={links[0].url!} target="_blank" rel="noreferrer">
          <ExternalLink size={12} /> Aç
        </a>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)}>
          <ExternalLink size={12} /> Aç
        </Button>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Nereye gitmek istersin?">
        <div className="grid gap-2">
          {links.map((link) => (
            <a
              key={link.label}
              className={linkClass}
              href={link.url!}
              target="_blank"
              rel="noreferrer"
              onClick={() => setOpen(false)}
            >
              {link.label === "GitHub deposu" ? <Github size={14} /> : <ExternalLink size={14} />}
              {link.label}
            </a>
          ))}
        </div>
      </Modal>
    </>
  );
}

function ProjectSettings({ project }: { project: Project }) {
  const online = useOnline();
  const toast = useToast();

  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/projects/${project.id}`, body),
    onSuccess: () => {
      invalidateAfter("project.write");
    },
    onError: () => toast.push("Kaydedilemedi.", { tone: "danger" }),
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/projects/${project.id}`),
    onSuccess: () => {
      invalidateAfter("project.write");
      toast.push("Proje silindi — bağlı görevler durmaya devam ediyor.", { tone: "ok" });
    },
  });

  return (
    <div>
      <div className="min-w-0 stack-y-4">
        <Section title="Proje bilgisi">
          <div className="grid gap-3">
            <Field label="GitHub deposu" hint={<GithubConnection project={project} />}>
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
                onSave={(value) =>
                  patch.mutate({ url: value ? (/^https?:\/\//i.test(value) ? value : `https://${value}`) : null })
                }
              />
            </Field>
          </div>
        </Section>

        <ProjectResources project={project} editing />
        <div className="flex justify-end border-t border-subtle pt-3">
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
        </div>
      </div>
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
    onSuccess: (project) => {
      invalidateAfter("project.write");
      onDone(project.id);
    },
    onError: () => toast.push("Proje açılamadı.", { tone: "danger" }),
  });

  return (
    <div>
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
    </div>
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
