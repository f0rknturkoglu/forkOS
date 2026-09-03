import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Check,
  CircleDot,
  ExternalLink,
  GitBranch,
  GitCommitHorizontal,
  Github,
  GitPullRequest,
  MessageSquare,
  Plus,
  RefreshCw,
  Star,
} from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { GithubIssue, GithubRepoPanel, Project } from "@/core/types";
import { Button, Chip, Empty, Metric, MetricStrip, RowList, Section, cx, relativeTime, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";

export type GithubActivityFilter = "all" | "issue" | "pull" | "commit";

type GithubCommit = GithubRepoPanel["commits"][number];

export type GithubActivity =
  | {
      key: string;
      kind: "issue" | "pull";
      title: string;
      url: string;
      timestamp: string | null;
      issue: GithubIssue;
    }
  | {
      key: string;
      kind: "commit";
      title: string;
      url: string;
      timestamp: string | null;
      commit: GithubCommit;
    };

function timestampValue(value: string | null): number {
  if (!value) return 0;
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

/**
 * Son 7 gundeki commit sayisi (kayan pencere). `/commits` listesi en yeni 10
 * commit ile sinirli -- yogun repolarda sayi en fazla 10 gorunur; istemci
 * yeni ag cagrisi yapmaz, yaklasim bilincli bir tavan.
 */
function commitsThisWeek(commits: GithubRepoPanel["commits"]): number {
  const cutoff = Date.now() - 7 * 86_400_000;
  return commits.filter((commit) => {
    if (!commit.committed_at) return false;
    const at = new Date(commit.committed_at).getTime();
    return !Number.isNaN(at) && at >= cutoff;
  }).length;
}

export function githubActivities(data: GithubRepoPanel): GithubActivity[] {
  const issues: GithubActivity[] = data.issues.map((issue) => ({
    key: `issue:${issue.number}`,
    kind: "issue",
    title: issue.title,
    url: issue.url,
    timestamp: issue.updated_at ?? issue.created_at,
    issue,
  }));
  const pulls: GithubActivity[] = data.pulls.map((issue) => ({
    key: `pull:${issue.number}`,
    kind: "pull",
    title: issue.title,
    url: issue.url,
    timestamp: issue.updated_at ?? issue.created_at,
    issue,
  }));
  const commits: GithubActivity[] = data.commits.map((commit) => ({
    key: `commit:${commit.sha}`,
    kind: "commit",
    title: commit.message,
    url: commit.url,
    timestamp: commit.committed_at,
    commit,
  }));
  return [...issues, ...pulls, ...commits].sort(
    (left, right) => timestampValue(right.timestamp) - timestampValue(left.timestamp),
  );
}

export function githubPanelError(error: unknown): { title: string; detail: string; settings: boolean } {
  const message = error instanceof Error ? error.message.toLocaleLowerCase("en-US") : "";
  if (message.includes("401") || message.includes("bad credentials")) {
    return {
      title: "GitHub bağlantısı geçersiz.",
      detail: "Ayarlar'dan kişisel erişim tokenını yenile.",
      settings: true,
    };
  }
  if (message.includes("rate limit")) {
    return {
      title: "GitHub istek sınırına ulaşıldı.",
      detail: "Bir süre sonra yeniden dene; bağlı token daha yüksek limit sağlar.",
      settings: false,
    };
  }
  if (message.includes("403")) {
    return {
      title: "GitHub bu depoya erişime izin vermedi.",
      detail: "Tokenın repository access ve read izinlerini kontrol et.",
      settings: true,
    };
  }
  if (message.includes("404")) {
    return {
      title: "Depo bulunamadı veya erişim izni yok.",
      detail: "owner/repo değerini ve private repo erişimini kontrol et.",
      settings: true,
    };
  }
  return {
    title: "GitHub verisi alınamadı.",
    detail: "Bağlantıyı kontrol edip yeniden dene.",
    settings: false,
  };
}

export function GithubPanel({ project }: { project: Project }) {
  const [filter, setFilter] = useState<GithubActivityFilter>("all");
  const online = useOnline();
  const toast = useToast();
  const path = `/projects/${project.id}/github`;
  const query = useQuery({
    queryKey: ["project-github", project.id],
    queryFn: () => api.get<GithubRepoPanel>(path),
    enabled: Boolean(project.github_repo),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const refresh = useMutation({
    mutationFn: () => api.get<GithubRepoPanel>(`${path}?refresh=true`),
    onSuccess: async () => {
      await query.refetch();
    },
  });
  const toTodo = useMutation({
    mutationFn: (number: number) =>
      api.post<{ duplicate: boolean; id?: string; title: string }>(`${path}/issues`, { number }),
    onSuccess: (result) => {
      invalidateAfter("project.write");
      toast.push(result.duplicate ? "Bu issue zaten görevlerde." : "Görev oluşturuldu", {
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

  const data = refresh.data ?? query.data;
  const activities = data ? githubActivities(data) : [];
  const visible = filter === "all" ? activities : activities.filter((activity) => activity.kind === filter);
  const counts: Record<GithubActivityFilter, number> = {
    all: activities.length,
    issue: data?.issues.length ?? 0,
    pull: data?.pulls.length ?? 0,
    commit: data?.commits.length ?? 0,
  };
  const weekCommits = data ? commitsThisWeek(data.commits) : 0;
  // Liste 10 commit ile sinirli: pencere tamamen doluysa gercek sayi
  // bilinmez, "10+" olarak gosterilir (yaklasim, yeni ag cagrisi yok).
  const weekCommitsLabel = data && data.commits.length === 10 && weekCommits === 10 ? "10+" : String(weekCommits);
  const error = refresh.error ?? query.error;

  return (
    <Section
      title={
        <span className="inline-flex items-center gap-1.5">
          <Github size={13} className="text-feed-gh" /> GitHub
        </span>
      }
      bodyClassName="p-0"
    >
      {query.isLoading && !data ? (
        <GithubLoading />
      ) : query.isError && !data ? (
        <div className="p-3.5">
          <GithubError error={query.error} />
        </div>
      ) : data ? (
        <>
          <header className="flex flex-wrap items-start gap-3 border-b border-subtle px-3.5 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={data.url}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate text-body font-medium text-primary transition hover:text-accent"
                >
                  {data.repo}
                </a>
                <Chip tone={data.private ? "warn" : "neutral"}>{data.private ? "private" : "public"}</Chip>
                {data.default_branch && (
                  <Chip variant="outline" icon={<GitBranch size={10} />}>
                    {data.default_branch}
                  </Chip>
                )}
              </div>
              <p className="mt-1 text-meta text-muted">
                GitHub'dan {relativeTime(data.fetched_at)} alındı
                {!data.authenticated && " · token bağlı değil"}
              </p>
              <div
                data-testid="github-repo-stats"
                className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-meta text-secondary"
              >
                <span className="inline-flex items-center gap-1" title="GitHub yıldızı">
                  <Star size={11} className="text-feed-gh" aria-hidden />
                  <span className="tabular-nums">{data.stars}</span>
                </span>
                <span>
                  <span className="tabular-nums">{data.open_issues}</span> açık issue
                </span>
                {data.language && <span>{data.language}</span>}
                <span>son push {data.pushed_at ? relativeTime(data.pushed_at) : "—"}</span>
                <span className="inline-flex items-center gap-1">
                  <GitCommitHorizontal size={11} aria-hidden />
                  bu hafta <span className="tabular-nums">{weekCommitsLabel}</span> commit
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <a
                href={data.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-8 items-center gap-1.5 rounded-control border border-subtle px-3 text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
              >
                GitHub'da aç <ExternalLink size={11} />
              </a>
              <Button
                size="sm"
                onClick={() => refresh.mutate()}
                disabled={!online || refresh.isPending}
                ariaLabel="GitHub verisini yenile"
              >
                <RefreshCw size={12} className={refresh.isPending ? "animate-spin" : undefined} />
                {refresh.isPending ? "Yenileniyor" : "Yenile"}
              </Button>
            </div>
          </header>

          {!online && (
            <p className="border-b border-warn-border bg-warn-surface px-3.5 py-2 text-meta text-warn">
              Çevrimdışı mod: kayıtlı GitHub verisi okunabilir; yenileme ve görev oluşturma kapalı.
            </p>
          )}
          {error && (
            <div className="border-b border-danger-border bg-danger-surface px-3.5 py-2.5">
              <GithubError error={error} compact />
            </div>
          )}

          <div className="p-3.5">
            <MetricStrip className="grid-cols-2 sm:grid-cols-4">
              <Metric label="açık issue" value={data.issues.length} />
              <Metric label="açık PR" value={data.pulls.length} />
              <Metric label="son push" value={data.pushed_at ? relativeTime(data.pushed_at) : "—"} />
              <Metric label="ana dil" value={data.language ?? "—"} />
            </MetricStrip>

            {data.description && (
              <p className="border-b border-subtle py-3 text-meta text-secondary">{data.description}</p>
            )}

            <div className="flex flex-wrap items-center gap-1.5 border-b border-subtle py-2.5">
              {(
                [
                  ["all", "Tümü"],
                  ["issue", "Issue"],
                  ["pull", "PR"],
                  ["commit", "Commit"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  aria-pressed={filter === id}
                  onClick={() => setFilter(id)}
                  className={cx(
                    "rounded-control border px-2.5 py-1 text-meta transition",
                    filter === id
                      ? "border-strong bg-surface-sunken font-medium text-primary"
                      : "border-transparent text-muted hover:border-subtle hover:text-primary",
                  )}
                >
                  {label} <span className="tabular-nums text-muted">{counts[id]}</span>
                </button>
              ))}
            </div>

            {visible.length === 0 ? (
              <Empty>{filter === "all" ? "Bu depoda henüz hareket yok." : "Bu filtrede hareket yok."}</Empty>
            ) : (
              <RowList as="ul">
                {visible.map((activity) => (
                  <ActivityRow
                    key={activity.key}
                    activity={activity}
                    online={online}
                    pending={
                      activity.kind === "issue" && toTodo.isPending && toTodo.variables === activity.issue.number
                    }
                    onToTodo={(number) => toTodo.mutate(number)}
                  />
                ))}
              </RowList>
            )}
          </div>
        </>
      ) : null}
    </Section>
  );
}

function GithubLoading() {
  return (
    <div role="status" aria-label="GitHub verisi yükleniyor" className="animate-pulse space-y-3 p-3.5">
      <div className="h-8 rounded-control bg-surface-sunken" />
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="h-14 rounded-control bg-surface-sunken" />
        ))}
      </div>
      <div className="h-20 rounded-control bg-surface-sunken" />
    </div>
  );
}

function GithubError({ error, compact = false }: { error: unknown; compact?: boolean }) {
  const state = githubPanelError(error);
  return (
    <div className={cx("text-meta", !compact && "py-2 text-center")}>
      <p className="font-medium text-danger">{state.title}</p>
      <p className="text-secondary">
        {state.detail}
        {state.settings && (
          <>
            {" "}
            <a href="#/settings" className="text-accent hover:underline">
              Ayarları aç
            </a>
          </>
        )}
      </p>
    </div>
  );
}

function ActivityRow({
  activity,
  online,
  pending,
  onToTodo,
}: {
  activity: GithubActivity;
  online: boolean;
  pending: boolean;
  onToTodo: (number: number) => void;
}) {
  const icon =
    activity.kind === "commit" ? (
      <GitCommitHorizontal size={14} className="text-feed-gh" />
    ) : activity.kind === "pull" ? (
      <GitPullRequest size={14} className="text-accent" />
    ) : (
      <CircleDot size={14} className="text-ok" />
    );
  const label = activity.kind === "commit" ? "Commit" : activity.kind === "pull" ? "PR" : "Issue";

  return (
    <li data-testid="github-activity-row" className="flex min-w-0 items-start gap-2.5 py-2.5">
      <span className="mt-0.5 shrink-0" aria-hidden>
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="shrink-0 text-micro font-medium text-muted">{label}</span>
          <a
            href={activity.url}
            target="_blank"
            rel="noreferrer"
            className="truncate text-body font-medium text-primary transition hover:text-accent"
          >
            {activity.title}
          </a>
        </div>
        {activity.kind === "commit" ? (
          <p className="mt-0.5 flex flex-wrap gap-x-2 text-meta text-muted">
            <span className="tabular-nums">{activity.commit.sha}</span>
            {activity.commit.author && <span>{activity.commit.author}</span>}
            {activity.timestamp && <span>{relativeTime(activity.timestamp)}</span>}
          </p>
        ) : (
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-muted">
            <span className="tabular-nums">#{activity.issue.number}</span>
            {activity.issue.author && <span>{activity.issue.author}</span>}
            {activity.issue.comments > 0 && (
              <span className="inline-flex items-center gap-1">
                <MessageSquare size={11} /> {activity.issue.comments}
              </span>
            )}
            {activity.timestamp && <span>{relativeTime(activity.timestamp)}</span>}
            {activity.issue.labels.slice(0, 3).map((label) => (
              <Chip key={label} size="xs" variant="outline">
                {label}
              </Chip>
            ))}
          </p>
        )}
      </div>
      {activity.kind === "issue" &&
        (activity.issue.todo_id ? (
          <Chip tone="ok" icon={<Check size={10} />}>
            Görevlerde
          </Chip>
        ) : (
          <Button
            size="sm"
            disabled={!online || pending}
            onClick={() => onToTodo(activity.issue.number)}
            ariaLabel="Göreve dönüştür"
            className="px-2.5"
          >
            {pending ? <RefreshCw size={11} className="animate-spin" /> : <Plus size={11} />}
            <span className="hidden sm:inline">{pending ? "Dönüştürülüyor" : "Göreve dönüştür"}</span>
          </Button>
        ))}
    </li>
  );
}
