import { invalidateAfter } from "@/core/invalidation";
import { useId, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, ChevronRight, Plus } from "lucide-react";

import { api } from "@/core/api";
import type { MediaItem } from "@/core/types";
import type { components } from "@/generated/api-schema";
import { Button, Chip, IconButton, Section, cx, relativeTime } from "@/core/ui";
import { formatTrDate } from "@/lib/date";
import { measureLabel } from "./MediaProgressActions";

type MediaUnit = components["schemas"]["MediaUnitOut"];
type MediaConsumption = components["schemas"]["MediaConsumptionOut"];

interface UnitNode {
  unit: MediaUnit;
  parentId: string | null;
  children: UnitNode[];
}

const SUFFIX_BY_VOWEL: Record<string, string> = {
  a: "ı",
  e: "i",
  ı: "ı",
  i: "i",
  o: "u",
  ö: "ü",
  u: "u",
  ü: "ü",
};

function lastVowelSuffix(word: string): string {
  for (let index = word.length - 1; index >= 0; index -= 1) {
    const suffix = SUFFIX_BY_VOWEL[word[index]];
    if (suffix) return suffix;
  }
  return "i";
}

/** "bölüm" → "bölümü" (belirtme hali) — "Birinci bölümü tamamla" etiketi için. */
function accusative(word: string): string {
  return word + lastVowelSuffix(word);
}

/** "bölüm" → "bölümün" (tamlayan hali) — "…tamamlamasını geri al" etiketi için. */
function genitive(word: string): string {
  return word + lastVowelSuffix(word) + "n";
}

/** Tür bazlı bölüm başlığı: müzikte "Parçalar", diğerlerinde "Bölümler". */
function unitSectionTitle(kind: string): string {
  return kind === "music" || kind === "audiobook" || kind === "podcast" ? "Parçalar" : "Bölümler";
}

/**
 * `detail.units` yuvalanmis (`children`) da duz (`parent_id`) de gelebilir;
 * ikisini de ayni agaca cevirir. `parent_id` hic yoksa duz liste kalir --
 * sahte hiyerarsi uretilmez.
 */
function unitForest(units: MediaUnit[]): UnitNode[] {
  const flat: { unit: MediaUnit; parentId: string | null }[] = [];
  const walk = (rows: MediaUnit[], parentId: string | null) => {
    for (const unit of rows) {
      flat.push({ unit, parentId: parentId ?? unit.parent_id ?? null });
      if (unit.children?.length) walk(unit.children, unit.id);
    }
  };
  walk(units, null);

  const nodes = new Map<string, UnitNode>();
  for (const { unit, parentId } of flat) nodes.set(unit.id, { unit, parentId, children: [] });
  const roots: UnitNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.parentId ? nodes.get(node.parentId) : undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  return roots;
}

function UnitRow({
  node,
  item,
  online,
  completedIds,
  onToggle,
  onQuick,
  busy,
}: {
  node: UnitNode;
  item: MediaItem;
  online: boolean;
  completedIds: Set<string>;
  onToggle: (unit: MediaUnit, completed: boolean) => void;
  onQuick: (unit: MediaUnit) => void;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  const { unit } = node;
  const completed = completedIds.has(unit.id);
  const notReleased = unit.release_at ? new Date(unit.release_at).getTime() > Date.now() : false;
  const measure = unit.progress_measure ?? item.progress_measure ?? "item";
  const meta = [
    unit.unit_type,
    unit.release_at
      ? new Date(unit.release_at).getTime() > Date.now()
        ? formatTrDate(unit.release_at)
        : relativeTime(unit.release_at)
      : null,
    unit.duration_min != null ? `${unit.duration_min} dk` : null,
    unit.progress_total != null ? `${unit.progress_total} ${measureLabel(measure)}` : null,
    notReleased ? "henüz yayınlanmadı" : null,
  ].filter(Boolean);

  return (
    <li className="py-2">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        {node.children.length > 0 ? (
          <button
            type="button"
            aria-expanded={open}
            aria-controls={listId}
            aria-label={open ? `${unit.title} alt kayıtlarını gizle` : `${unit.title} alt kayıtlarını göster`}
            onClick={() => setOpen((value) => !value)}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary"
          >
            <ChevronRight size={13} aria-hidden="true" className={cx("transition-transform", open && "rotate-90")} />
          </button>
        ) : (
          <span aria-hidden="true" className="h-6 w-6 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-body font-medium text-primary">
            {unit.number != null ? `${unit.number}. ` : ""}
            {unit.title}
          </p>
          {meta.length > 0 && <p className="mt-0.5 text-meta text-muted">{meta.join(" · ")}</p>}
        </div>
        {completed && (
          <Chip size="xs" tone="ok">
            Tamamlandı
          </Chip>
        )}
        {node.children.length === 0 && (
          <IconButton
            title={`${unit.title} ilerlemesini kaydet`}
            disabled={!online || busy}
            onClick={() => onQuick(unit)}
          >
            <Plus size={13} aria-hidden="true" />
          </IconButton>
        )}
        <Button
          size="sm"
          variant={completed ? "secondary" : "primary"}
          disabled={!online || busy || notReleased}
          onClick={() => onToggle(unit, completed)}
        >
          {completed ? (
            `${genitive(unit.title)} tamamlamasını geri al`
          ) : (
            <>
              <Check size={13} aria-hidden="true" /> {accusative(unit.title)} tamamla
            </>
          )}
        </Button>
      </div>
      {node.children.length > 0 && open && (
        <ul id={listId} className="mt-1 divide-y divide-subtle border-l border-subtle pl-3 sm:pl-4">
          {node.children.map((child) => (
            <UnitRow
              key={child.unit.id}
              node={child}
              item={item}
              online={online}
              completedIds={completedIds}
              onToggle={onToggle}
              onQuick={onQuick}
              busy={busy}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * Unit hiyerarsisi (sezon→bölüm, albüm→parça, cilt→bölüm).
 *
 * Tamamlanma durumu tuketim gecmisinden turetilir: her unit icin EN YENI event
 * belirleyicidir, boylece geri alinan bir tamamlama tekrar "tamamlandı"
 * gorunmez. `details/summary` yerine Section + liste kullanilir; acma/kapama
 * dugmesi `aria-expanded`/`aria-controls` tasir.
 */
export function UnitTree({
  item,
  units,
  consumptions,
  online,
}: {
  item: MediaItem;
  units: MediaUnit[];
  consumptions: MediaConsumption[];
  online: boolean;
}) {
  const toggle = useMutation({
    mutationFn: ({ unit, completed }: { unit: MediaUnit; completed: boolean }) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, {
        action: completed ? "uncomplete_unit" : "complete_unit",
        unit_id: unit.id,
        measure: unit.progress_measure ?? item.progress_measure ?? "item",
        client_uuid: crypto.randomUUID(),
      }),
    onSuccess: () => invalidateAfter("media.write"),
  });
  const quick = useMutation({
    mutationFn: (unit: MediaUnit) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, {
        action: "quick",
        amount: 1,
        unit_id: unit.id,
        measure: unit.progress_measure ?? item.progress_measure ?? "item",
        client_uuid: crypto.randomUUID(),
      }),
    onSuccess: () => invalidateAfter("media.write"),
  });

  const forest = unitForest(units);
  if (forest.length === 0) return null;

  const completedIds = new Set<string>();
  const seen = new Set<string>();
  for (const entry of consumptions) {
    if (entry.unit_id == null) continue;
    const id = String(entry.unit_id);
    if (seen.has(id)) continue;
    seen.add(id);
    if (entry.action === "complete_unit") completedIds.add(id);
  }

  const failure = toggle.error ?? quick.error;

  return (
    <Section title={unitSectionTitle(item.kind)} hint={`${forest.length} üst kayıt`}>
      <ul className="divide-y divide-subtle">
        {forest.map((node) => (
          <UnitRow
            key={node.unit.id}
            node={node}
            item={item}
            online={online}
            completedIds={completedIds}
            onToggle={(unit, completed) => toggle.mutate({ unit, completed })}
            onQuick={(unit) => quick.mutate(unit)}
            busy={toggle.isPending || quick.isPending}
          />
        ))}
      </ul>
      {failure && (
        <p role="alert" className="mt-2 text-meta text-danger">
          Bölüm durumu güncellenemedi: {failure.message}
        </p>
      )}
    </Section>
  );
}
