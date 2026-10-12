import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Plus, Unlink } from "lucide-react";
import { RelatedPanel } from "@/core/RelatedPanel";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Empty, Field, IconButton, Input, Section, useToast } from "@/core/ui";
import type { Project } from "@/core/types";
import type { components } from "@/generated/api-schema";
import { useOnline } from "@/lib/hooks";

type Resource = components["schemas"]["ProjectResourceOut"];

export function ProjectResources({ project, editing = false }: { project: Project; editing?: boolean }) {
  const online = useOnline();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  // A lost response is retried with the same identity and payload.
  const [request, setRequest] = useState<{ client_uuid: string; title: string; url: string } | null>(null);
  const query = useQuery({
    queryKey: ["project-resources", project.id],
    queryFn: () => api.get<Resource[]>(`/projects/${project.id}/resources`),
  });
  const add = useMutation({
    mutationFn: (body: NonNullable<typeof request>) => api.post(`/projects/${project.id}/resources`, body),
    onSuccess: () => {
      setTitle("");
      setUrl("");
      setRequest(null);
      invalidateAfter("project-resource.write");
    },
    onError: () => toast.push("Bağlantı kaydedilemedi. Yeniden deneyebilirsin.", { tone: "danger" }),
  });
  const unlink = useMutation({
    mutationFn: (id: string) => api.del("/links", { from_id: project.id, to_id: id, relation: "references" }),
    onSuccess: () => invalidateAfter("link.write"),
    onError: () => toast.push("Bağlantı kaldırılamadı.", { tone: "danger" }),
  });
  return (
    <Section title="Bağlantılar ve dokümanlar">
      {!editing && (project.url || project.github_repo) && (
        <div className="mb-3 flex flex-wrap gap-3 text-body">
          {project.github_repo && (
            <a
              className="flex items-center gap-2 text-primary hover:text-accent"
              href={`https://github.com/${project.github_repo}`}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={14} /> GitHub deposu
            </a>
          )}
          {project.url && (
            <a
              className="flex items-center gap-2 text-primary hover:text-accent"
              href={/^https?:\/\//i.test(project.url) ? project.url : `https://${project.url}`}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={14} /> Proje bağlantısı
            </a>
          )}
        </div>
      )}
      {editing && (
        <form
          className="mb-3 grid gap-2 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!online || add.isPending || !title.trim() || !url.trim()) return;
            const normalized = /^https?:\/\//i.test(url.trim()) ? url.trim() : `https://${url.trim()}`;
            const body =
              request?.title === title.trim() && request.url === normalized
                ? request
                : { client_uuid: crypto.randomUUID(), title: title.trim(), url: normalized };
            setRequest(body);
            add.mutate(body);
          }}
        >
          <Field label="Bağlantı adı">
            <Input
              ariaLabel="Bağlantı adı"
              value={title}
              onChange={setTitle}
              placeholder="Doküman, board, site…"
              disabled={add.isPending}
            />
          </Field>
          <Field label="Bağlantı adresi">
            <Input
              ariaLabel="Bağlantı adresi"
              value={url}
              onChange={setUrl}
              placeholder="https://…"
              disabled={add.isPending}
            />
          </Field>
          <Button type="submit" size="sm" disabled={!online || add.isPending || !title.trim() || !url.trim()}>
            <Plus size={14} /> Bağlantı ekle
          </Button>
        </form>
      )}
      {query.isError ? (
        <div role="alert">
          <p className="text-meta text-danger">Bağlantılar alınamadı.</p>
          <Button size="sm" onClick={() => void query.refetch()}>
            Yeniden dene
          </Button>
        </div>
      ) : query.isLoading ? (
        <p className="text-meta text-muted">Bağlantılar yükleniyor…</p>
      ) : !query.data?.length ? (
        <Empty>Henüz ek bağlantı yok. Proje ayarlarından ekleyebilirsin.</Empty>
      ) : (
        <ul className="stack-y-2">
          {query.data.map((item) => (
            <li key={item.id} className="flex min-w-0 items-center gap-2">
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="flex min-w-0 flex-1 items-center gap-2 text-body text-primary hover:text-accent"
              >
                <ExternalLink size={14} className="shrink-0" />
                <span className="truncate">{item.title}</span>
              </a>
              {editing && (
                <IconButton
                  title={`${item.title} bağlantısını kaldır`}
                  disabled={!online || unlink.isPending}
                  onClick={() => unlink.mutate(item.id)}
                >
                  <Unlink size={14} />
                </IconButton>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export function ProjectConnections({ project }: { project: Project }) {
  const query = useQuery({
    queryKey: ["project-resources", project.id],
    queryFn: () => api.get<Resource[]>(`/projects/${project.id}/resources`),
  });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ProjectResources project={project} />
      <RelatedPanel
        entityId={project.id}
        title="Bağlı kayıtlar"
        excludeEntityIds={query.data?.map((item) => item.id) ?? []}
      />
    </div>
  );
}
