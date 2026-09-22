import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { navigate, useHashRoute } from "@/app/router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, PanelRight, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  Drawer,
  Field,
  IconButton,
  Input,
  PageFrame,
  Modal,
  Section,
  Select,
  Tabs,
  cx,
  relativeTime,
  useToast,
  SkeletonRows,
} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import type { Project } from "@/core/types";
import { RelatedPanel } from "@/core/RelatedPanel";
import { GithubPanel } from "./GithubPanel";
import { ProjectTodos } from "./ProjectTodos";
import { Milestones } from "./Milestones";
import { MilestoneTimeline } from "./MilestoneTimeline";
import { ProjectActivityTimeline } from "./ProjectActivityTimeline";
import { ProjectJournalBridge } from "./ProjectJournalBridge";
import { ProjectKnowledgeNote } from "./ProjectKnowledgeNote";
import {
  Workspace,
  WorkspacePaneHeader,
  WorkspaceInspectorContent,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
  WorkspaceToolbar,
} from "@/core/workspace/Workspace";

const STATUSES = [
  { value: "active", label: "aktif", tone: "ok", dot: "bg-ok" },
  { value: "paused", label: "beklemede", tone: "warn", dot: "bg-warn" },
  { value: "done", label: "bitti", tone: "neutral", dot: "bg-icon" },
  { value: "idea", label: "fikir", tone: "accent", dot: "bg-accent" },
] as const;

const statusOf = (value: string) => STATUSES.find((item) => item.value === value) ?? STATUSES[0];
type ProjectView = "overview" | "work" | "activity";
const PROJECT_VIEWS = [
  { id: "overview", label: "Genel" },
  { id: "work", label: "İşler" },
  { id: "activity", label: "Geçmiş" },
];

/** Proje seçimi, aktif iş ve ikincil bağlam aynı çalışma alanında kalır. */
export function ProjectsPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus") ?? "";
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [view, setView] = useState<ProjectView>("overview");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [mobileInspectorOpen, setMobileInspectorOpen] = useState(false);
  const online = useOnline();

  const { data: projects = [], isLoading } = useQuery({
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
    setView("overview");
    setMobileInspectorOpen(false);
    navigate(`/projects?focus=${encodeURIComponent(id)}`, { replace: true });
  };

  return (
    <PageFrame className="py-3">
      {isLoading ? (
        <SkeletonRows rows={6} />
      ) : projects.length === 0 ? (
        <div className="space-y-4">
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
        <Workspace
          railAt="lg"
          className="grid-rows-[auto_minmax(0,1fr)] lg:grid-rows-1"
          inspectorAt="xl"
          inspector={inspectorOpen ? <ProjectInspector key={current.id} project={current} /> : undefined}
          rail={
            <WorkspaceRailContent className="max-h-64 lg:max-h-workspace-body">
              <WorkspaceRailGroup label="Projeler" hint={projects.length}>
                {projects.map((project) => {
                  const status = statusOf(project.status);
                  const active = project.id === selected;
                  return (
                    <WorkspaceRailButton
                      key={project.id}
                      label={project.title}
                      active={active}
                      selection
                      onClick={() => selectProject(project.id)}
                      onKeyDown={(event) => {
                        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
                        event.preventDefault();
                        const direction = event.key === "ArrowDown" ? 1 : -1;
                        const next =
                          (projects.findIndex((item) => item.id === project.id) + direction + projects.length) %
                          projects.length;
                        selectProject(projects[next].id);
                        const buttons = event.currentTarget
                          .closest("section")
                          ?.querySelectorAll<HTMLButtonElement>("button[aria-pressed]");
                        buttons?.[next]?.focus();
                      }}
                      icon={<span className={cx("h-2 w-2 rounded-full", status.dot)} />}
                      count={
                        project.last_activity_at
                          ? `${relativeTime(project.last_activity_at)} · ${status.label}`
                          : (project.github_repo ?? status.label)
                      }
                    />
                  );
                })}
              </WorkspaceRailGroup>
            </WorkspaceRailContent>
          }
        >
          <WorkspacePaneHeader
            title={current.title}
            hint={<Chip tone={statusOf(current.status).tone}>{statusOf(current.status).label}</Chip>}
          />
          <WorkspaceToolbar
            left={
              <Tabs
                value={view}
                onChange={setView}
                items={PROJECT_VIEWS}
                ariaLabel="Proje görünümü"
                panelId={() => "project-view"}
              />
            }
            right={
              <>
                <Button size="sm" className="xl:hidden" onClick={() => setMobileInspectorOpen(true)}>
                  <PanelRight size={14} /> Detaylar
                </Button>
                <Button
                  size="sm"
                  className="hidden xl:inline-flex"
                  ariaLabel={inspectorOpen ? "Detayları gizle" : "Detayları göster"}
                  onClick={() => setInspectorOpen((value) => !value)}
                >
                  <PanelRight size={14} /> Detaylar
                </Button>
                <Button variant="primary" size="sm" onClick={() => setAdding(true)} disabled={!online}>
                  <Plus size={14} /> Yeni proje
                </Button>
              </>
            }
          />
          <WorkspaceScrollArea className="p-4">
            <div id="project-view" role="tabpanel" className="mx-auto max-w-4xl space-y-4">
              <ProjectViewContent key={`${current.id}:${view}`} project={current} view={view} onView={setView} />
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
          <Drawer
            open={mobileInspectorOpen}
            onClose={() => setMobileInspectorOpen(false)}
            title={current.title}
            hint="Proje detayları"
          >
            <ProjectInspector key={current.id} project={current} />
          </Drawer>
        </Workspace>
      ) : null}
    </PageFrame>
  );
}

function ProjectViewContent({
  project,
  view,
  onView,
}: {
  project: Project;
  view: ProjectView;
  onView: (view: ProjectView) => void;
}) {
  if (view === "work") {
    return (
      <>
        <ProjectTodos project={project} />
        <Milestones project={project} />
        <GithubPanel project={project} />
      </>
    );
  }
  if (view === "activity") {
    return (
      <>
        <ProjectActivityTimeline projectId={project.id} />
        <ProjectJournalBridge projectId={project.id} />
      </>
    );
  }
  const nextMilestone = project.milestones.find((item) => !item.completed_at);
  const completed = project.milestones.filter((item) => item.completed_at).length;
  return (
    <>
      <Section title="Sıradaki adım">
        <p className="text-body text-primary">
          {project.next_action || nextMilestone?.title || "Henüz bir sonraki adım belirlenmedi."}
        </p>
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-subtle pt-3">
          <span className="text-meta text-secondary">
            Kilometre taşları: {completed}/{project.milestones.length}
          </span>
          <Button size="sm" onClick={() => onView("work")}>
            İşlere git
          </Button>
        </div>
      </Section>
      <MilestoneTimeline project={project} />
      <ProjectKnowledgeNote project={project} />
    </>
  );
}

function ProjectInspector({ project }: { project: Project }) {
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

  return (
    <WorkspaceInspectorContent title="Proje detayları">
      <div className="min-w-0 space-y-4">
        <Section
          title="Proje bilgisi"
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
          <div className="grid gap-3">
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

        <RelatedPanel entityId={project.id} title="Bağlı kayıtlar" />
      </div>
    </WorkspaceInspectorContent>
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
