import type { Milestone, Project } from "@/core/types";
import { Section, cx } from "@/core/ui";

/**
 * Kilometre tasi zaman cizelgesi: Milestones listesinin kronolojik ozeti.
 *
 * Veri kaynagi proje listesine gomulu mevcut milestone kayitlaridir (ayri
 * sorgu acilmaz -- denetim bulgusu). due_at varsa tas geciken/yaklasan
 * grubuna, completed_at varsa tamamlanan grubuna duser; tamamlananlar
 * cizgili gosterilir. Tarihsiz acik taslar yalnizca cizelgede baska icerik
 * varken sona eklenir; hicbir tarih/bitis bilgisi yoksa bilesen hicbir sey
 * cizmez -- o durumda liste zaten butun bilgiyi tasiyor.
 */
export function MilestoneTimeline({ project }: { project: Project }) {
  const items = project.milestones ?? [];
  const done = items.filter((item) => item.completed_at);
  const open = items.filter((item) => !item.completed_at);
  const openDated = open.filter((item) => item.due_at);
  const undated = open.filter((item) => !item.due_at);
  if (openDated.length === 0 && done.length === 0) return null;

  // Gecikenler en eski (en cok geciken) ustte; yaklasanlar en yakin ustte.
  const byDueAt = (left: Milestone, right: Milestone) => timestamp(left.due_at) - timestamp(right.due_at);
  const overdue = openDated.filter((item) => (dueDayDiff(item.due_at) ?? 0) < 0).sort(byDueAt);
  const upcoming = openDated.filter((item) => (dueDayDiff(item.due_at) ?? 0) >= 0).sort(byDueAt);
  const completed = [...done].sort((left, right) => timestamp(right.completed_at) - timestamp(left.completed_at));

  const groups = [
    { key: "overdue", label: "Geciken", dot: "bg-danger", rows: overdue },
    { key: "upcoming", label: "Yaklaşan", dot: "bg-accent", rows: upcoming },
    { key: "done", label: "Tamamlanan", dot: "bg-ok", rows: completed },
    { key: "undated", label: "Tarihsiz", dot: "bg-icon", rows: undated },
  ].filter((group) => group.rows.length > 0);

  return (
    <Section title="Zaman çizelgesi">
      {groups.map((group) => (
        <div key={group.key} className="mb-2 last:mb-0">
          {groups.length > 1 && <p className="label-caps mb-1">{group.label}</p>}
          <ul>
            {group.rows.map((item) => (
              <TimelineRow key={item.id} item={item} dot={group.dot} />
            ))}
          </ul>
        </div>
      ))}
    </Section>
  );
}

function TimelineRow({ item, dot }: { item: Milestone; dot: string }) {
  const done = Boolean(item.completed_at);
  const badge = done ? null : dueBadge(item.due_at);
  const dateText =
    done && item.due_at ? new Date(item.due_at).toLocaleDateString("tr-TR", { day: "numeric", month: "short" }) : null;
  return (
    <li data-testid="milestone-timeline-row" className="flex min-w-0 items-center gap-2.5 py-1.5">
      <span aria-hidden className={cx("h-2 w-2 shrink-0 rounded-full", dot)} />
      <span className={cx("min-w-0 flex-1 truncate text-body", done ? "text-muted line-through" : "text-primary")}>
        {item.title}
      </span>
      {dateText && <span className="shrink-0 text-meta text-muted">{dateText}</span>}
      {badge && (
        <span
          className={cx("shrink-0 text-meta font-medium", badge.tone)}
          title={item.due_at ? new Date(item.due_at).toLocaleDateString("tr-TR") : undefined}
        >
          {badge.text}
        </span>
      )}
    </li>
  );
}

function timestamp(value: string | null): number {
  if (!value) return 0;
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

/** Yerel gun sinirina gore bugunden fark: gecmiste negatif, bugun 0. */
function dueDayDiff(dueAt: string | null): number | null {
  if (!dueAt) return null;
  const due = new Date(dueAt).getTime();
  if (Number.isNaN(due)) return null;
  const startOfLocalDay = (value: number) => {
    const day = new Date(value);
    return new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
  };
  return Math.round((startOfLocalDay(due) - startOfLocalDay(Date.now())) / 86_400_000);
}

function dueBadge(dueAt: string | null): { text: string; tone: string } | null {
  const diff = dueDayDiff(dueAt);
  if (diff === null) return null;
  if (diff < 0) {
    const days = -diff;
    return { text: days === 1 ? "1 gün gecikti" : `${days} gün gecikti`, tone: "text-danger" };
  }
  if (diff === 0) return { text: "bugün", tone: "text-accent" };
  if (diff === 1) return { text: "yarın", tone: "text-accent" };
  return { text: `${diff} gün kaldı`, tone: "text-muted" };
}
