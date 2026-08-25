import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CircleDot, GitCommitHorizontal, GitPullRequest, MessageSquare, Plus, RefreshCw, Star,
} from "lucide-react";
import { api } from "@/core/api";
import { Empty, RowList, Section, cx, relativeTime, useToast } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";
import type { GithubIssue, GithubRepoPanel, Project } from "@/core/types";

type Tab = "issues" | "pulls" | "commits";

/**
 * Projeye bagli deponun paneli.
 *
 * Issue'lar buradan tek tiklamayla goreve donusur ve projeye baglanir --
 * "GitHub'da issue var, forkOS'ta gorev yok" ikiligini kapatan yer burasi.
 */
export function GithubPanel({ project }: { project: Project }) {
  const [tab, setTab] = useState<Tab>("issues");
  const online = useOnline();
  const invalidate = useInvalidate();
  const toast = useToast();

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["project-github", project.id],
    queryFn: () => api.get<GithubRepoPanel>(`/projects/${project.id}/github`),
    enabled: Boolean(project.github_repo),
    staleTime: 5 * 60_000,
    retry: false,
  });

  const toTodo = useMutation({
    mutationFn: (number: number) =>
      api.post<{ duplicate: boolean; title: string }>(
        `/projects/${project.id}/github/issues`, { number }),
    onSuccess: (result) => {
      invalidate("project-todos", "todos", "activity", "tags");
      toast.push(result.duplicate ? "Bu issue zaten görev olarak duruyor." : "Görev oluşturuldu", {
        tone: result.duplicate ? "warn" : "ok",
      });
    },
    onError: () => toast.push("Görev oluşturulamadı.", { tone: "danger" }),
  });

  if (!project.github_repo) {
    return (
      <Section title="GitHub">
        <Empty>
          Bu projeye depo bağlı değil. Yukarıdaki “GitHub deposu” alanına
          <span className="text-primary"> sahip/depo</span> yaz.
        </Empty>
      </Section>
    );
  }

  const TABS: { id: Tab; label: string; count: number }[] = [
    { id: "issues", label: "Issue", count: data?.issues.length ?? 0 },
    { id: "pulls", label: "PR", count: data?.pulls.length ?? 0 },
    { id: "commits", label: "Commit", count: data?.commits.length ?? 0 },
  ];

  return (
    <Section
      title="GitHub"
      hint={data ? <a href={data.url} target="_blank" rel="noreferrer"
        className="text-accent hover:underline">{data.repo} ↗</a> : project.github_repo}
      action={
        <button type="button" onClick={() => refetch()} disabled={isFetching}
          title="Tazele" className="text-muted transition hover:text-primary disabled:opacity-40">
          <RefreshCw size={13} className={isFetching ? "animate-spin" : undefined} />
        </button>
      }
    >
      {isLoading ? (
        <p className="py-3 text-meta text-muted">Yükleniyor…</p>
      ) : isError ? (
        <p className="py-3 text-meta text-danger">
          {(error as Error)?.message || "GitHub'a ulaşılamadı."}
        </p>
      ) : data ? (
        <>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-b border-subtle pb-3 sm:grid-cols-4">
            <Stat icon={<Star size={12} />} label="yıldız" value={data.stars.toLocaleString("tr-TR")} />
            <Stat icon={<CircleDot size={12} />} label="açık issue" value={data.open_issues} />
            <Stat label="dil" value={data.language ?? "—"} />
            <Stat label="son push"
              value={data.pushed_at ? relativeTime(data.pushed_at) : "—"} />
          </dl>

          {data.description && (
            <p className="border-b border-subtle py-2.5 text-meta text-secondary">
              {data.description}
            </p>
          )}

          <div className="flex items-center gap-2 py-2.5 text-meta">
            {TABS.map((item) => (
              <button key={item.id} type="button" onClick={() => setTab(item.id)}
                aria-pressed={tab === item.id}
                className={cx(
                  "rounded-control border px-2.5 py-1 transition",
                  tab === item.id
                    ? "border-strong bg-surface-sunken text-primary"
                    : "border-subtle text-muted hover:border-strong hover:text-primary",
                )}>
                {item.label} <span className="text-muted">{item.count}</span>
              </button>
            ))}
            {!data.authenticated && (
              <span className="ml-auto text-micro text-muted">
                token yok · 60 istek/saat
              </span>
            )}
          </div>

          {tab === "commits" ? (
            data.commits.length === 0 ? <Empty>Commit yok.</Empty> : (
              <RowList as="ul">
                {data.commits.map((commit) => (
                  <li key={commit.sha} className="flex items-start gap-2.5 py-2">
                    <GitCommitHorizontal size={13} className="mt-0.5 shrink-0 text-icon" />
                    <div className="min-w-0 flex-1">
                      <a href={commit.url} target="_blank" rel="noreferrer"
                        className="block truncate text-body text-primary hover:text-accent">
                        {commit.message}
                      </a>
                      <p className="text-meta text-muted">
                        <span className="numeral">{commit.sha}</span>
                        {commit.author && ` · ${commit.author}`}
                        {commit.committed_at && ` · ${relativeTime(commit.committed_at)}`}
                      </p>
                    </div>
                  </li>
                ))}
              </RowList>
            )
          ) : (
            <IssueList
              items={tab === "issues" ? data.issues : data.pulls}
              kind={tab}
              disabled={!online || toTodo.isPending}
              onToTodo={(number) => toTodo.mutate(number)}
            />
          )}
        </>
      ) : null}
    </Section>
  );
}

function Stat({ icon, label, value }: { icon?: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="flex items-center gap-1 text-meta text-muted">{icon} {label}</dt>
      <dd className="truncate text-body text-primary">{value}</dd>
    </div>
  );
}

function IssueList({
  items, kind, disabled, onToTodo,
}: {
  items: GithubIssue[];
  kind: "issues" | "pulls";
  disabled: boolean;
  onToTodo: (number: number) => void;
}) {
  if (items.length === 0) {
    return <Empty>{kind === "issues" ? "Açık issue yok." : "Açık PR yok."}</Empty>;
  }
  return (
    <RowList as="ul">
      {items.map((item) => (
        <li key={item.number} className="group flex items-start gap-2.5 py-2">
          {kind === "issues"
            ? <CircleDot size={13} className="mt-1 shrink-0 text-ok" />
            : <GitPullRequest size={13} className={cx("mt-1 shrink-0", item.draft ? "text-icon" : "text-accent")} />}
          <div className="min-w-0 flex-1">
            <a href={item.url} target="_blank" rel="noreferrer"
              className="block truncate text-body font-medium text-primary hover:text-accent">
              {item.title}
            </a>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-meta text-muted">
              <span className="numeral">#{item.number}</span>
              {item.author && <span>{item.author}</span>}
              {item.comments > 0 && (
                <span className="flex items-center gap-1"><MessageSquare size={11} /> {item.comments}</span>
              )}
              {item.updated_at && <span>{relativeTime(item.updated_at)}</span>}
              {item.labels.slice(0, 3).map((label) => (
                <span key={label} className="rounded border border-subtle px-1.5 text-micro leading-4">
                  {label}
                </span>
              ))}
            </p>
          </div>
          {kind === "issues" && (
            <button type="button" disabled={disabled} onClick={() => onToTodo(item.number)}
              title="Görev oluştur"
              className="flex shrink-0 items-center gap-1 rounded-control border border-subtle px-2 py-1 text-meta text-muted opacity-0 transition hover:border-strong hover:text-primary focus-visible:opacity-100 group-hover:opacity-100 disabled:opacity-40">
              <Plus size={12} /> görev
            </button>
          )}
        </li>
      ))}
    </RowList>
  );
}
