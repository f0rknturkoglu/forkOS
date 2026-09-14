import { useEffect, useState } from "react";
import { Archive, ArchiveRestore, FolderCog, Plus, Trash2 } from "lucide-react";
import type { StudyAreaStats, StudyTreeNode, StudyTree } from "@/core/types";
import {
  Button,
  Checkbox,
  Empty,
  FilterChip,
  IconButton,
  Input,
  Modal,
  Select,
  Skeleton,
  SkeletonRows,
} from "@/core/ui";
import {
  TOPIC_STATUSES,
  statusLabel,
  type TopicQuickFilter,
  type TopicQuickKey,
  type TopicStatusFilter,
} from "./learningLabels";
import { TopicTree } from "./TopicTree";

/** Alan rengi -> nokta sinifi. Semantik token'lar; sabit hex yok. */
const AREA_DOT: Record<string, string> = {
  accent: "bg-accent",
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
  icon: "bg-icon",
};

const AREA_COLOR_LABEL: Record<string, string> = {
  "": "Renk yok",
  accent: "Vurgu (mavi)",
  ok: "Başarı (yeşil)",
  warn: "Uyarı (amber)",
  danger: "Tehlike (kırmızı)",
  icon: "Nötr (gri)",
};

const QUICK_FILTERS: { id: TopicQuickKey; label: string; hint: string }[] = [
  { id: "today", label: "Bugün", hint: "Bugün tekrarı gelen ya da bugün çalışılan konular" },
  { id: "studying", label: "Çalışılıyor", hint: "Üzerinde çalıştığın konular" },
  { id: "due", label: "Tekrar zamanı", hint: "Tekrarı bugüne kadar gelmiş konular" },
];

const STATUS_FILTERS: { id: TopicStatusFilter; label: string }[] = [
  { id: "all", label: "Tümü" },
  ...TOPIC_STATUSES.map((status) => ({ id: status as TopicStatusFilter, label: statusLabel(status) })),
];

interface LearningRailProps {
  online: boolean;
  /* Alanlar */
  areas: StudyAreaStats[];
  areasState: "loading" | "error" | "ready";
  onRetryAreas: () => void;
  areaId: string;
  onSelectArea: (id: string) => void;
  areaQuery: string;
  onAreaQuery: (value: string) => void;
  includeArchived: boolean;
  onIncludeArchived: (value: boolean) => void;
  selectedArea?: StudyAreaStats;
  onManageAreas: () => void;
  /* Konu arama + filtreler */
  topicQuery: string;
  onTopicQuery: (value: string) => void;
  statusFilter: TopicStatusFilter;
  onStatusFilter: (value: TopicStatusFilter) => void;
  quickFilter: TopicQuickFilter;
  onQuickFilter: (value: TopicQuickFilter) => void;
  quickCounts: Record<TopicQuickKey, number>;
  /* Agac */
  tree?: StudyTree;
  treeState: "loading" | "error" | "ready";
  onRetryTree: () => void;
  nodes: StudyTreeNode[];
  filtered: boolean;
  selectedId: string;
  revealPath: string[];
  onSelectTopic: (id: string) => void;
  onTaskTopic: (node: StudyTreeNode) => void;
  onFocusTopic: (node: StudyTreeNode) => void;
  /* Yeni konu */
  newTopicTitle: string;
  onNewTopicTitle: (value: string) => void;
  newTopicRoot: boolean;
  onNewTopicRoot: (value: boolean) => void;
  parentTitle?: string;
  onAddTopic: () => void;
  addPending: boolean;
  /* Alan yonetimi */
  manageOpen: boolean;
  onManageClose: () => void;
  onRenameArea: (id: string, title: string) => void;
  onColorArea: (id: string, color: string) => void;
  onArchiveArea: (id: string, archived: boolean) => void;
  onDeleteArea: (area: StudyAreaStats) => void;
  onCreateArea: (title: string) => void;
  areaPending: boolean;
}

/** Ogrenme rayi: alan secimi + filtreler + konu agaci + yeni konu. */
export function LearningRail(props: LearningRailProps) {
  const {
    online,
    areas,
    areasState,
    onRetryAreas,
    areaId,
    onSelectArea,
    areaQuery,
    onAreaQuery,
    includeArchived,
    onIncludeArchived,
    selectedArea,
    onManageAreas,
    topicQuery,
    onTopicQuery,
    statusFilter,
    onStatusFilter,
    quickFilter,
    onQuickFilter,
    quickCounts,
    tree,
    treeState,
    onRetryTree,
    nodes,
    filtered,
    selectedId,
    revealPath,
    onSelectTopic,
    onTaskTopic,
    onFocusTopic,
    newTopicTitle,
    onNewTopicTitle,
    newTopicRoot,
    onNewTopicRoot,
    parentTitle,
    onAddTopic,
    addPending,
    manageOpen,
    onManageClose,
    onRenameArea,
    onColorArea,
    onArchiveArea,
    onDeleteArea,
    onCreateArea,
    areaPending,
  } = props;

  const needle = areaQuery.trim().toLocaleLowerCase("tr");
  const listed = areas.filter((area) => {
    const visible = includeArchived || !area.archived_at;
    return visible && (!needle || area.title.toLocaleLowerCase("tr").includes(needle));
  });
  // Secili alan arama disinda kalsa da listede kalir (bos secim gorunmesin).
  const options = listed.some((area) => area.id === areaId)
    ? listed
    : areas.filter((area) => area.id === areaId).concat(listed);

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Input
          value={areaQuery}
          onChange={onAreaQuery}
          placeholder="Alan ara"
          ariaLabel="Alan ara"
          className="w-full"
        />
        {areasState === "loading" ? (
          <Skeleton className="h-9 w-full" />
        ) : areasState === "error" ? (
          <div
            role="alert"
            className="space-y-2 rounded-control border border-danger-border bg-danger-surface px-3 py-2"
          >
            <p className="text-meta text-danger">Alanlar yüklenemedi.</p>
            <Button size="sm" onClick={onRetryAreas}>
              Yeniden dene
            </Button>
          </div>
        ) : (
          <Select
            value={areaId}
            onChange={onSelectArea}
            ariaLabel="Çalışma alanı"
            className="w-full"
            disabled={options.length === 0}
          >
            <option value="">Alan seç…</option>
            {options.map((area) => (
              <option key={area.id} value={area.id}>
                {area.archived_at ? `${area.title} (arşiv)` : area.title}
              </option>
            ))}
          </Select>
        )}
        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip
            label="Arşivli alanlar"
            active={includeArchived}
            onClick={() => onIncludeArchived(!includeArchived)}
          />
          <Button size="sm" onClick={onManageAreas} ariaLabel="Alan yönetimi">
            <FolderCog size={14} /> Alan yönetimi
          </Button>
        </div>
        {selectedArea && (
          <p className="flex items-center gap-1.5 text-meta text-muted">
            <span
              aria-hidden="true"
              className={`h-2 w-2 shrink-0 rounded-full ${AREA_DOT[selectedArea.color ?? ""] ?? "bg-icon"}`}
            />
            <span className="tabular-nums">
              {selectedArea.topic_count} konu · {selectedArea.stale_count} bayat · {selectedArea.resource_count} kaynak
            </span>
          </p>
        )}
      </div>

      <div className="space-y-2 border-t border-subtle pt-3">
        <Input
          value={topicQuery}
          onChange={onTopicQuery}
          placeholder="Konu ara"
          ariaLabel="Konu ara"
          className="w-full"
        />
        <div className="flex flex-wrap gap-1.5">
          {STATUS_FILTERS.map((item) => (
            <FilterChip
              key={item.id}
              label={item.label}
              active={statusFilter === item.id}
              onClick={() => onStatusFilter(item.id)}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_FILTERS.map((item) => (
            <FilterChip
              key={item.id}
              label={item.label}
              count={quickCounts[item.id]}
              active={quickFilter === item.id}
              onClick={() => onQuickFilter(quickFilter === item.id ? "none" : item.id)}
            />
          ))}
        </div>
      </div>

      <div className="border-t border-subtle pt-3">
        {treeState === "loading" ? (
          <SkeletonRows rows={6} />
        ) : treeState === "error" ? (
          <div
            role="alert"
            className="space-y-2 rounded-control border border-danger-border bg-danger-surface px-3 py-2"
          >
            <p className="text-meta text-danger">Konu ağacı yüklenemedi.</p>
            <Button size="sm" onClick={onRetryTree}>
              Yeniden dene
            </Button>
          </div>
        ) : nodes.length === 0 ? (
          <Empty>
            {filtered ? "Bu filtreyle eşleşen konu yok. Aramayı temizleyip yeniden dene." : "Bu alanda henüz konu yok."}
          </Empty>
        ) : (
          <TopicTree
            key={`${tree?.area.id ?? ""}|${topicQuery.trim()}|${statusFilter}|${quickFilter}`}
            nodes={nodes}
            selectedId={selectedId}
            revealPath={revealPath}
            expandAll={filtered}
            onSelect={onSelectTopic}
            onTask={onTaskTopic}
            onFocusTopic={onFocusTopic}
            actionsDisabled={!online}
          />
        )}
      </div>

      <form
        className="space-y-2 border-t border-subtle pt-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (newTopicTitle.trim() && areaId) onAddTopic();
        }}
      >
        <div className="flex gap-2">
          <Input
            value={newTopicTitle}
            onChange={onNewTopicTitle}
            placeholder="Yeni konu"
            ariaLabel="Yeni konu başlığı"
            className="min-w-0 flex-1"
          />
          <Button
            type="submit"
            disabled={!online || addPending || !areaId}
            title={online ? undefined : "Çevrimdışı: yazma kapalı"}
            ariaLabel="Konu ekle"
          >
            <Plus size={14} /> Ekle
          </Button>
        </div>
        <Checkbox checked={newTopicRoot} onChange={onNewTopicRoot} label="Kök konu olarak ekle" disabled={!online} />
        {!newTopicRoot && parentTitle && <p className="text-meta text-muted">«{parentTitle}» altına eklenecek.</p>}
      </form>

      <AreaManager
        open={manageOpen}
        onClose={onManageClose}
        areas={areas}
        online={online}
        pending={areaPending}
        onRename={onRenameArea}
        onColor={onColorArea}
        onArchive={onArchiveArea}
        onDelete={onDeleteArea}
        onCreate={onCreateArea}
      />
    </div>
  );
}

/** Alan yonetimi: yeniden adlandir, renklendir, arsivle, kalici sil. */
function AreaManager({
  open,
  onClose,
  areas,
  online,
  pending,
  onRename,
  onColor,
  onArchive,
  onDelete,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  areas: StudyAreaStats[];
  online: boolean;
  pending: boolean;
  onRename: (id: string, title: string) => void;
  onColor: (id: string, color: string) => void;
  onArchive: (id: string, archived: boolean) => void;
  onDelete: (area: StudyAreaStats) => void;
  onCreate: (title: string) => void;
}) {
  const [draft, setDraft] = useState("");
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Alan yönetimi"
      hint="Yeniden adlandır, renklendir ve arşivle. Silme yerine arşivleme birincil yoldur."
      ariaLabel="Alan yönetimi"
      className="sm:max-w-2xl"
    >
      <div className="space-y-2">
        {areas.length === 0 && <Empty>Henüz alan yok. Aşağıdan ilk alanı ekle.</Empty>}
        {areas.map((area) => (
          <AreaRow
            key={area.id}
            area={area}
            online={online}
            pending={pending}
            onRename={onRename}
            onColor={onColor}
            onArchive={onArchive}
            onDelete={onDelete}
          />
        ))}
        <form
          className="flex gap-2 pt-1"
          onSubmit={(event) => {
            event.preventDefault();
            if (draft.trim()) {
              onCreate(draft);
              setDraft("");
            }
          }}
        >
          <Input
            value={draft}
            onChange={setDraft}
            disabled={!online}
            placeholder="Yeni alan"
            ariaLabel="Yeni alan adı"
            className="min-w-0 flex-1"
          />
          <Button type="submit" disabled={!online || pending} title={online ? undefined : "Çevrimdışı: yazma kapalı"}>
            Alan ekle
          </Button>
        </form>
      </div>
    </Modal>
  );
}

function AreaRow({
  area,
  online,
  pending,
  onRename,
  onColor,
  onArchive,
  onDelete,
}: {
  area: StudyAreaStats;
  online: boolean;
  pending: boolean;
  onRename: (id: string, title: string) => void;
  onColor: (id: string, color: string) => void;
  onArchive: (id: string, archived: boolean) => void;
  onDelete: (area: StudyAreaStats) => void;
}) {
  const [draft, setDraft] = useState(area.title);
  useEffect(() => setDraft(area.title), [area.title]);
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-subtle pb-2">
      <span
        aria-hidden="true"
        className={`h-2.5 w-2.5 shrink-0 rounded-full ${AREA_DOT[area.color ?? ""] ?? "bg-icon"}`}
      />
      <Input
        value={draft}
        onChange={setDraft}
        disabled={!online}
        onBlur={(value) => {
          const next = value.trim();
          if (next && next !== area.title) onRename(area.id, next);
          else setDraft(area.title);
        }}
        ariaLabel={`${area.title} adı`}
        className="min-w-48 flex-1"
      />
      <Select
        value={area.color ?? ""}
        onChange={(value) => onColor(area.id, value)}
        disabled={!online}
        ariaLabel={`${area.title} rengi`}
      >
        {Object.entries(AREA_COLOR_LABEL).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </Select>
      <span className="tabular-nums text-meta text-muted">
        {area.topic_count} konu · {area.resource_count} kaynak
      </span>
      <Button
        size="sm"
        disabled={!online || pending}
        onClick={() => onArchive(area.id, !area.archived_at)}
        title={online ? (area.archived_at ? "Arşivden çıkar" : "Arşivle") : "Çevrimdışı: yazma kapalı"}
        ariaLabel={area.archived_at ? `${area.title} alanını geri aç` : `${area.title} alanını arşivle`}
      >
        {area.archived_at ? <ArchiveRestore size={14} /> : <Archive size={14} />}
        {area.archived_at ? "Geri aç" : "Arşivle"}
      </Button>
      <IconButton
        title="Alanı kalıcı olarak sil"
        tone="danger"
        disabled={!online || pending}
        onClick={() => onDelete(area)}
      >
        <Trash2 size={14} />
      </IconButton>
    </div>
  );
}
