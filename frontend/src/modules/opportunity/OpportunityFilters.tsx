/**
 * Fırsat filtre yüzeyi: üst satır + aktif chip'ler + gelişmiş panel.
 *
 * Tasarım kuralı: filtreler sonuçların önünü kapatmaz. Varsayılan durumda
 * yalnızca tek satırlık bir araç çubuğu görünür; gelişmiş filtreler ayrı bir
 * ortalanmış bir modalda açılır. Aktif olan her filtre
 * mutlaka bir chip olarak görünür ve tek başına kaldırılabilir.
 */

import { useMemo, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { LayoutGrid, Kanban, List, RotateCcw, Search, SlidersHorizontal, X } from "lucide-react";
import { Button, Chip, FilterChip, IconButton, Input, Modal, Select, Section, cx } from "@/core/ui";
import { sourceLabel } from "@/core/labels";
import { ARCHETYPE_LABELS, RECOMMENDATION_LABELS, REMOTE_LABELS, STATUS_LABELS, jobCategoryLabel } from "./labels";
import type { OpportunityBrowseFilters } from "./opportunityBrowse";
import { PROFILE_MATCH_PRESETS, activeFilterChips, clearAllFilters } from "./filterState";
import { SCORE_STATE_PRESETS } from "./scoreDomain";
import { ScoreRangeControl } from "./ScoreRangeControl";

interface FilterBarProps {
  leading?: ReactNode;
  filters: OpportunityBrowseFilters;
  facets: Record<string, Record<string, number>>;
  /** Sonuç sayacı: yüklenirken eski sayı korunur, sahte 0/0 gösterilmez. */
  shown: number;
  total: number;
  loading: boolean;
  view: "rows" | "grid" | "kanban";
  onView: (view: "rows" | "grid" | "kanban") => void;
  onChange: (next: OpportunityBrowseFilters) => void;
  /** Arama kutusunun taslağı: her tuşta anında görünür, API'ye debounce'lu gider. */
  searchValue: string;
  onSearchChange: (value: string) => void;
  /** Bildirim bölgesi: sonuç değişimini ekran okuyucuya duyurur. */
  liveMessage: string;
}

const SORT_LABELS: Record<string, string> = {
  score: "Skor: yüksekten düşüğe",
  skill_match: "Profil uyumu: en yüksek",
  score_asc: "Skor: düşükten yükseğe",
  newest: "En yeni",
  oldest: "En eski",
  deadline: "Son tarihe göre",
};

function facetChips(
  facets: Record<string, Record<string, number>>,
  key: string,
  labels: Record<string, string>,
  selected: string | undefined,
  onPick: (value: string) => void,
) {
  return Object.entries(facets[key] ?? {})
    .sort(([, left], [, right]) => right - left)
    .map(([value, count]) => (
      <FilterChip
        key={value}
        label={labels[value] ?? value}
        count={count}
        active={selected === value}
        onClick={() => onPick(selected === value ? "" : value)}
      />
    ));
}

export function OpportunityFilterBar({
  leading,
  filters,
  facets,
  shown,
  total,
  loading,
  view,
  onView,
  onChange,
  searchValue,
  onSearchChange,
  liveMessage,
}: FilterBarProps) {
  const [panelOpen, setPanelOpen] = useState(false);
  const chips = useMemo(() => activeFilterChips(filters), [filters]);
  const update = (changes: Partial<OpportunityBrowseFilters>) => onChange({ ...filters, ...changes, offset: 0 });
  const sourceStatus = filters.source_status ?? "active";
  const clearFilters = () => {
    onChange(clearAllFilters(filters));
    // Taslak da temizlenmeli: yoksa debounce onu 250 ms sonra geri yazar ve
    // "temizlendi" denen arama geri gelir.
    onSearchChange("");
  };
  const viewOptions = [
    { id: "rows", title: "Yatay satırlar", Icon: List },
    { id: "grid", title: "Karesel kartlar", Icon: LayoutGrid },
    { id: "kanban", title: "Kanban panosu", Icon: Kanban },
  ] as const;

  return (
    <div className="space-y-2">
      <div role="toolbar" aria-label="Fırsat filtreleri" className="flex flex-wrap items-center gap-2">
        {leading}
        <div className="relative min-w-0 flex-[2_1_16rem]">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-icon" />
          <Input
            value={searchValue}
            onChange={onSearchChange}
            placeholder="Başlık, kurum, konum ya da kaynakta ara…"
            ariaLabel="Fırsatlarda ara"
            className="w-full pl-9"
          />
        </div>

        <Select
          ariaLabel="Sıralama"
          value={filters.sort}
          onChange={(sort) => update({ sort: sort as OpportunityBrowseFilters["sort"] })}
        >
          {(filters.section === "jobs" ? ["score", "skill_match", "score_asc"] : ["newest", "oldest", "deadline"]).map(
            (key) => (
              <option key={key} value={key}>
                {SORT_LABELS[key]}
              </option>
            ),
          )}
          {filters.section === "jobs" && <option value="newest">En yeni</option>}
        </Select>

        <span className="inline-flex">
          <Button
            size="sm"
            variant={panelOpen || chips.length > 0 ? "secondary" : "ghost"}
            ariaExpanded={panelOpen}
            onClick={() => setPanelOpen((open) => !open)}
          >
            <SlidersHorizontal size={12} /> Filtreler
            {chips.length > 0 && (
              <span className="ml-0.5 rounded-full bg-accent px-1.5 text-micro tabular-nums text-canvas">
                {chips.length}
              </span>
            )}
          </Button>
          <FilterPanelModal
            open={panelOpen}
            onClose={() => setPanelOpen(false)}
            filters={filters}
            facets={facets}
            onChange={onChange}
            onClear={clearFilters}
          />
        </span>

        <span className="ml-auto flex items-center gap-2">
          <span
            className={cx("text-meta tabular-nums", loading ? "text-muted" : "text-secondary")}
            aria-live="polite"
            aria-busy={loading}
          >
            {loading ? "Yükleniyor…" : `${shown} / ${total} kayıt`}
          </span>
          <span
            className="flex items-center gap-1 rounded-control border border-subtle p-0.5"
            role="group"
            aria-label="Görünüm"
          >
            {viewOptions.map((option) => (
              <IconButton
                key={option.id}
                title={option.title}
                ariaPressed={view === option.id}
                onClick={() => onView(option.id)}
                className={view === option.id ? "bg-surface-sunken text-primary" : "border-transparent"}
              >
                <option.Icon size={14} />
              </IconButton>
            ))}
          </span>
        </span>
      </div>

      {chips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5" aria-label="Aktif filtreler">
          {chips.map((chip) => (
            <Chip key={`${chip.key}:${chip.label}`} tone="accent">
              <span className="inline-flex items-center gap-1">
                <span>{chip.label}</span>
                <button
                  type="button"
                  onClick={() => onChange(chip.clear(filters))}
                  className="ml-0.5 cursor-pointer hover:opacity-75"
                  aria-label={`${chip.label} filtresini kaldır`}
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          ))}
          <Button size="sm" variant="ghost" onClick={clearFilters}>
            <RotateCcw size={12} /> Tümünü temizle
          </Button>
        </div>
      )}

      <p className="sr-only" role="status">
        {liveMessage}
      </p>
    </div>
  );
}

function FilterPanelModal({
  open,
  onClose,
  filters,
  facets,
  onChange,
  onClear,
}: {
  open: boolean;
  onClose: () => void;
  filters: OpportunityBrowseFilters;
  facets: Record<string, Record<string, number>>;
  onChange: (next: OpportunityBrowseFilters) => void;
  onClear: () => void;
}) {
  const update = (changes: Partial<OpportunityBrowseFilters>) => onChange({ ...filters, ...changes, offset: 0 });
  // Bölüme göre geçerli filtreler: backend'e GİTMEYEN bir filtre panelde de
  // gösterilmez, aksi halde kullanıcı sonucu değiştirmeyen kontrollerle uğraşır.
  const jobs = filters.section === "jobs";
  const announcements = filters.section === "announcements";

  if (!open) return null;

  return createPortal(
    <Modal
      open={open}
      onClose={onClose}
      title="Filtreler"
      hint="Seçimler sonuçlara anında uygulanır."
      className="flex flex-col !overflow-hidden sm:max-w-2xl [&>header]:shrink-0 [&>footer]:shrink-0 [&>[data-modal-body]]:min-h-0 [&>[data-modal-body]]:overflow-y-auto"
      footer={
        <div className="flex items-center justify-between gap-3">
          <Button size="sm" variant="ghost" onClick={onClear}>
            <RotateCcw size={12} /> Temizle
          </Button>
          <Button size="sm" onClick={onClose}>
            Sonuçları göster
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {jobs && (
          <Section title="Profil / beceri uyumu">
            <div className="flex flex-wrap gap-1.5">
              {PROFILE_MATCH_PRESETS.map((preset) => {
                const active =
                  preset.min === filters.min_skill_match &&
                  preset.max === filters.max_skill_match &&
                  (preset.state ?? undefined) === (filters.skill_match_state ?? undefined);
                return (
                  <FilterChip
                    key={preset.label}
                    label={preset.label}
                    active={active}
                    onClick={() =>
                      update(
                        active
                          ? {
                              min_skill_match: undefined,
                              max_skill_match: undefined,
                              skill_match_state: undefined,
                              skill_tier: undefined,
                            }
                          : {
                              min_skill_match: preset.min,
                              max_skill_match: preset.max,
                              skill_match_state: preset.state,
                              skill_tier: preset.tier,
                            },
                      )
                    }
                  />
                );
              })}
            </div>
            <p className="mt-1.5 text-micro text-muted">
              Bu oran yalnızca profilindeki becerilerle ilan metninin örtüşmesidir; CV dosyasıyla yapılan değerlendirme
              ilan detayındaki “Uyum” sekmesindedir.
            </p>
          </Section>
        )}

        {jobs && (
          <Section title="Kategori">
            <div className="flex flex-wrap gap-1.5">
              {facetChips(
                facets,
                "categories",
                Object.fromEntries(Object.keys(facets.categories ?? {}).map((key) => [key, jobCategoryLabel(key)])),
                filters.category,
                (value) => update({ category: value }),
              )}
            </div>
          </Section>
        )}

        {announcements && (
          <Section title="Duyuru türü">
            <div className="flex flex-wrap gap-1.5">
              {facetChips(
                facets,
                "announcement_sources",
                { ylsy: "YLSY", osym: "ÖSYM", other: "Diğer" },
                filters.announcement_source,
                (value) => update({ announcement_source: value as "" | "ylsy" | "osym" | "other" }),
              )}
            </div>
          </Section>
        )}

        <Section title="Konum & çalışma biçimi">
          <div className="space-y-2">
            <div className="flex flex-wrap gap-1.5">
              {facetChips(
                facets,
                "regions",
                { TR: "Türkiye", EU: "Avrupa", OTHER: "Diğer", UNKNOWN: "Konum bilinmiyor" },
                filters.region,
                (value) => update({ region: value }),
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {/* "Bilinmiyor" kovası facet'ten gelir (REMOTE_LABELS.unknown);
                  elle ikinci bir chip eklemek aynı filtreyi iki kez gösteriyordu. */}
              {facetChips(facets, "remote", REMOTE_LABELS as Record<string, string>, filters.remote, (value) =>
                update({ remote: value }),
              )}
            </div>
          </div>
        </Section>

        {jobs && (
          <Section title="Kariyer analizi & rol tipi">
            <div className="flex flex-wrap gap-1.5">
              {facetChips(facets, "recommendations", RECOMMENDATION_LABELS, filters.recommendation, (value) =>
                update({ recommendation: value }),
              )}
              {facetChips(facets, "archetypes", ARCHETYPE_LABELS, filters.archetype, (value) =>
                update({ archetype: value }),
              )}
            </div>
          </Section>
        )}

        {jobs && (
          <Section title="Beceri">
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={filters.skill ?? ""}
                onChange={(skill) => update({ skill })}
                placeholder="örn. kubernetes, python"
                ariaLabel="Beceriye göre filtrele"
                className="max-w-xs"
              />
              {filters.skill && (
                <Button size="sm" variant="ghost" onClick={() => update({ skill: undefined })}>
                  Kaldır
                </Button>
              )}
            </div>
          </Section>
        )}

        <Section title="Kaynak">
          <div className="flex flex-wrap items-center gap-1.5">
            <FilterChip
              label="Manuel Eklenenler"
              count={facets.sources?.manual}
              active={filters.source === "manual"}
              onClick={() => update({ source: filters.source === "manual" ? "" : "manual" })}
            />
            <FilterChip
              label="Eklenti"
              count={facets.sources?.extension}
              active={filters.source === "extension"}
              onClick={() => update({ source: filters.source === "extension" ? "" : "extension" })}
            />
            <Select
              ariaLabel="Kaynak"
              value={filters.source ?? ""}
              onChange={(source) => update({ source })}
              className="max-w-full"
            >
              <option value="">Tüm kaynaklar</option>
              {Object.entries(facets.sources ?? {})
                .sort(([left], [right]) => sourceLabel(left).localeCompare(sourceLabel(right), "tr"))
                .map(([source, count]) => (
                  <option key={source} value={source}>
                    {sourceLabel(source)} · {count}
                  </option>
                ))}
            </Select>
          </div>
        </Section>

        <Section title="Durum">
          <div className="flex flex-wrap gap-1.5">
            {facetChips(facets, "statuses", STATUS_LABELS, filters.status, (value) => update({ status: value }))}
          </div>
        </Section>

        {jobs && (
          <Section title="Skor">
            <ScoreRangeControl
              min={filters.min_score}
              max={filters.max_score}
              onChange={(min, max) => update({ min_score: min, max_score: max })}
            />
            <div className="flex flex-wrap items-center gap-1.5">
              {SCORE_STATE_PRESETS.map((preset) => (
                <FilterChip
                  key={preset.label}
                  label={preset.label}
                  active={(filters.score_state ?? undefined) === preset.state}
                  onClick={() => update({ score_state: preset.state })}
                />
              ))}
              <Button size="sm" variant="ghost" onClick={() => update({ score_state: undefined })}>
                Temizle
              </Button>
            </div>
            <p className="mt-1.5 text-micro text-muted">
              “Hesaplanmadı”, hızlı uygunluk skoru henüz üretilmemiş ilanları getirir; 0 puan ile karışmaz.
            </p>
          </Section>
        )}

        {(jobs || announcements) && (
          <Section title="Kaynak durumu">
            <div className="flex flex-wrap gap-1.5">
              {(
                [
                  { id: "active", label: "Yayında", hint: "Kaynakta hâlâ görünen kayıtlar" },
                  { id: "stale", label: "Kaynakta bulunamıyor", hint: "Kaynakta kaybolmuş kayıtlar" },
                  { id: "all", label: "Tümü", hint: "İkisi birlikte" },
                ] as const
              ).map((option) => (
                <FilterChip
                  key={option.id}
                  label={option.label}
                  count={
                    option.id === "stale"
                      ? Object.entries(facets.source_statuses ?? {})
                          .filter(([status]) => status !== "active")
                          .reduce((sum, [, count]) => sum + count, 0)
                      : facets.source_statuses?.[option.id]
                  }
                  active={(filters.source_status ?? "active") === option.id}
                  onClick={() => update({ source_status: option.id })}
                />
              ))}
            </div>
            <p className="mt-1.5 text-micro text-muted">
              “Kaynakta bulunamıyor” kayıtları varsayılan akışta gösterilmez; başvurduğun kayıtlar burada da
              erişilebilir kalır.
            </p>
          </Section>
        )}

        {announcements && (
          <Section title="Tarih">
            <div className="flex flex-wrap items-center gap-1.5">
              {[30, 90, 365].map((days) => (
                <FilterChip
                  key={days}
                  label={days === 365 ? "Son 1 yıl" : `Son ${days} gün`}
                  active={filters.period_days === days}
                  onClick={() => update({ period_days: filters.period_days === days ? undefined : days })}
                />
              ))}
              <Select
                ariaLabel="Duyuru yılı"
                value={filters.year ? String(filters.year) : ""}
                onChange={(value) => update({ year: value ? Number(value) : undefined })}
              >
                <option value="">Tüm yıllar</option>
                {Object.keys(facets.years ?? {})
                  .sort((left, right) => Number(right) - Number(left))
                  .map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
              </Select>
            </div>
          </Section>
        )}

        <p className="text-micro text-muted">
          Çalışma biçimi kovaları kaynak metninden türetilir; “Çalışma biçimi bilinmiyor” ilanda bu alanın hiç
          yazılmadığı kayıtları toplar.
        </p>
      </div>
    </Modal>,
    document.body,
  );
}
