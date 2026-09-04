import { useEffect, useState } from "react";
import { Button, Chip, DualRange, FilterChip, Section, Select } from "@/core/ui";
import { sourceLabel } from "@/core/labels";
import {
  ARCHETYPE_LABELS,
  RECOMMENDATION_LABELS,
  REMOTE_LABELS,
  STATUSES,
  archetypeLabel,
  recommendationLabel,
  statusLabel,
  type RemoteKind,
} from "./labels";
import type { OpportunityBrowseFilters } from "./opportunityBrowse";
import { RotateCcw, SlidersHorizontal, X } from "lucide-react";

interface Props {
  filters: OpportunityBrowseFilters;
  facets: Record<string, Record<string, number>>;
  onChange: (next: OpportunityBrowseFilters) => void;
}

const SCORE_PRESETS = [
  { label: "80–100", min: 80, max: 100 },
  { label: "70–100", min: 70, max: 100 },
  { label: "40–69", min: 40, max: 69.9 },
  { label: "0–39", min: 0, max: 39.9 },
  { label: "Elendi", min: -1, max: -1 },
] as const;

const SKILL_MATCH_PRESETS = [
  { label: "%70+ Uyum", tier: "high", min: 0.7 },
  { label: "%40–%69 Uyum", tier: "mid", min: 0.4 },
  { label: "Tüm Eşleşmeler", tier: "any", min: 0.01 },
] as const;

function scoreLabel(value: number): string {
  return value === -1 ? "Elendi" : String(value);
}

function ScoreSlider({
  minValue,
  maxValue,
  onCommit,
}: {
  minValue: number;
  maxValue: number;
  onCommit: (minValue: number, maxValue: number) => void;
}) {
  const [draftMin, setDraftMin] = useState(minValue);
  const [draftMax, setDraftMax] = useState(maxValue);

  useEffect(() => setDraftMin(minValue), [minValue]);
  useEffect(() => setDraftMax(maxValue), [maxValue]);

  const commit = () => {
    if (draftMin !== minValue || draftMax !== maxValue) onCommit(draftMin, draftMax);
  };

  return (
    <div
      className="rounded-control border border-subtle bg-surface-sunken/40 px-4 py-2.5"
      onPointerUp={commit}
      onPointerCancel={commit}
      onKeyUp={commit}
      onBlur={commit}
    >
      <div className="mb-1 flex items-center justify-between gap-4 text-meta">
        <span className="text-secondary">
          Minimum <strong className="font-medium text-primary">{scoreLabel(draftMin)}</strong>
        </span>
        <span className="text-secondary">
          Maksimum <strong className="font-medium text-primary">{scoreLabel(draftMax)}</strong>
        </span>
      </div>
      <DualRange
        min={-1}
        max={100}
        minValue={draftMin}
        maxValue={draftMax}
        minAriaLabel="Minimum skor"
        maxAriaLabel="Maksimum skor"
        onChange={(nextMin, nextMax) => {
          setDraftMin(nextMin);
          setDraftMax(nextMax);
        }}
      />
      <div className="flex justify-between text-micro text-muted" aria-hidden>
        <span>Elendi</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}

export function OpportunityFilters({ filters, facets, onChange }: Props) {
  const [showAdvancedScore, setShowAdvancedScore] = useState(false);
  const update = (changes: Partial<OpportunityBrowseFilters>) => onChange({ ...filters, ...changes, offset: 0 });
  const scoreFilterActive = filters.min_score !== undefined || filters.max_score !== undefined;
  const skillMatchActive = filters.min_skill_match !== undefined || Boolean(filters.skill_tier);

  const activeFiltersCount =
    (filters.search ? 1 : 0) +
    (filters.category ? 1 : 0) +
    (filters.skill ? 1 : 0) +
    (scoreFilterActive ? 1 : 0) +
    (skillMatchActive ? 1 : 0) +
    (filters.remote ? 1 : 0) +
    (filters.region ? 1 : 0) +
    (filters.archetype ? 1 : 0) +
    (filters.recommendation ? 1 : 0) +
    (filters.status ? 1 : 0) +
    (filters.source ? 1 : 0) +
    (filters.announcement_source ? 1 : 0) +
    (filters.period_days ? 1 : 0) +
    (filters.year ? 1 : 0);

  const clearAllFilters = () => {
    onChange({
      ...filters,
      search: undefined,
      category: undefined,
      skill: undefined,
      min_score: undefined,
      max_score: undefined,
      min_skill_match: undefined,
      skill_tier: undefined,
      remote: undefined,
      region: undefined,
      archetype: undefined,
      recommendation: undefined,
      status: undefined,
      source: undefined,
      announcement_source: undefined,
      period_days: undefined,
      year: undefined,
      offset: 0,
    });
  };

  const chips = (
    values: Record<string, number> | undefined,
    selected: string | undefined,
    labels: Record<string, string>,
    key:
      "category" | "status" | "source" | "region" | "remote" | "announcement_source" | "archetype" | "recommendation",
  ) =>
    Object.entries(values ?? {}).map(([value, count]) => (
      <FilterChip
        key={value}
        label={labels[value] ?? value}
        count={count}
        active={selected === value}
        onClick={() => update({ [key]: selected === value ? "" : value })}
      />
    ));

  return (
    <div className="space-y-4">
      {/* Aktif Filtre Rozetleri & Hızlı Temizleme Barı */}
      {activeFiltersCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-control border border-subtle bg-surface-sunken/40 px-3 py-2 text-meta">
          <span className="text-secondary font-medium">Aktif Filtreler:</span>
          {scoreFilterActive && (
            <Chip tone="accent">
              <span className="inline-flex items-center gap-1">
                <span>
                  Uyum: {filters.min_score ?? -1}–{filters.max_score ?? 100}p
                </span>
                <button
                  type="button"
                  onClick={() => update({ min_score: undefined, max_score: undefined })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Skor filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {skillMatchActive && (
            <Chip tone="ok">
              <span className="inline-flex items-center gap-1">
                <span>CV Uyumu: ≥%{Math.round((filters.min_skill_match ?? 0) * 100)}</span>
                <button
                  type="button"
                  onClick={() => update({ min_skill_match: undefined, skill_tier: undefined })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="CV eşleşme filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {filters.remote && (
            <Chip tone="neutral">
              <span className="inline-flex items-center gap-1">
                <span>Çalışma: {REMOTE_LABELS[filters.remote as RemoteKind] ?? filters.remote}</span>
                <button
                  type="button"
                  onClick={() => update({ remote: "" })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Çalışma filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {filters.region && (
            <Chip tone="neutral">
              <span className="inline-flex items-center gap-1">
                <span>Konum: {filters.region === "TR" ? "Türkiye" : filters.region}</span>
                <button
                  type="button"
                  onClick={() => update({ region: "" })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Konum filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {filters.status && (
            <Chip tone="neutral">
              <span className="inline-flex items-center gap-1">
                <span>Durum: {statusLabel(filters.status)}</span>
                <button
                  type="button"
                  onClick={() => update({ status: "" })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Durum filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {filters.source && (
            <Chip tone="neutral">
              <span className="inline-flex items-center gap-1">
                <span>Kaynak: {sourceLabel(filters.source)}</span>
                <button
                  type="button"
                  onClick={() => update({ source: "" })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Kaynak filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {filters.recommendation && (
            <Chip
              tone={
                filters.recommendation === "pursue" ? "ok" : filters.recommendation === "consider" ? "warn" : "danger"
              }
            >
              <span className="inline-flex items-center gap-1">
                <span>Karar: {recommendationLabel(filters.recommendation)}</span>
                <button
                  type="button"
                  onClick={() => update({ recommendation: "" })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Karar filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          {filters.archetype && (
            <Chip tone="accent">
              <span className="inline-flex items-center gap-1">
                <span>Rol: {archetypeLabel(filters.archetype)}</span>
                <button
                  type="button"
                  onClick={() => update({ archetype: "" })}
                  className="hover:opacity-75 cursor-pointer ml-1"
                  title="Rol filtresini kaldır"
                >
                  <X size={12} />
                </button>
              </span>
            </Chip>
          )}
          <Button size="sm" variant="ghost" onClick={clearAllFilters} className="ml-auto text-meta">
            <RotateCcw size={12} /> Tümünü Temizle
          </Button>
        </div>
      )}

      {/* DUYURULAR İÇİN ÖZEL FİLTRE */}
      {filters.section === "announcements" && (
        <Section title="Duyuru türü">
          <div className="flex flex-wrap gap-2">
            {chips(
              facets.announcement_sources,
              filters.announcement_source,
              { ylsy: "YLSY", osym: "ÖSYM", other: "Diğer" },
              "announcement_source",
            )}
          </div>
        </Section>
      )}

      {/* İŞ İLANLARI İÇİN YENİLENMİŞ FİLTRELEME & SINIFLANDIRMA */}
      {filters.section === "jobs" && (
        <>
          {/* KATMAN 1: UYUM SKORU & CV EŞLEŞME SINIFLANDIRMASI */}
          <Section
            title="Uyum skoru"
            hint={scoreFilterActive ? `${filters.min_score ?? -1}–${filters.max_score ?? 100}p` : "Tüm skorlar"}
            action={
              <div className="flex items-center gap-2">
                <Button size="sm" variant="ghost" onClick={() => setShowAdvancedScore((prev) => !prev)}>
                  <SlidersHorizontal size={12} /> {showAdvancedScore ? "Sliderı Gizle" : "Hassas Aralık"}
                </Button>
                {scoreFilterActive && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => update({ min_score: undefined, max_score: undefined })}
                  >
                    Temizle
                  </Button>
                )}
              </div>
            }
          >
            <div className="space-y-3">
              {/* Uyum Skoru Kademeleri */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="label-caps mr-1 text-secondary">Skor Kademesi</span>
                {SCORE_PRESETS.map((preset) => {
                  const active = filters.min_score === preset.min && filters.max_score === preset.max;
                  return (
                    <FilterChip
                      key={preset.label}
                      label={preset.label}
                      active={active}
                      onClick={() =>
                        update(
                          active
                            ? { min_score: undefined, max_score: undefined }
                            : { min_score: preset.min, max_score: preset.max },
                        )
                      }
                    />
                  );
                })}
              </div>

              {/* CV & Beceri Eşleşme Kademeleri */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="label-caps mr-1 text-secondary">CV Eşleşmesi</span>
                {SKILL_MATCH_PRESETS.map((preset) => {
                  const active = filters.skill_tier === preset.tier;
                  return (
                    <FilterChip
                      key={preset.tier}
                      label={preset.label}
                      active={active}
                      onClick={() =>
                        update(
                          active
                            ? { min_skill_match: undefined, skill_tier: undefined }
                            : { min_skill_match: preset.min, skill_tier: preset.tier },
                        )
                      }
                    />
                  );
                })}
              </div>

              {/* Çift Yönlü Hassas Skor Slider'ı (Test uyumluluğu için her zaman DOM'da, varsayılan görünümde veya açıkken) */}
              <div className={showAdvancedScore ? "pt-2 block" : "pt-2 hidden lg:block"}>
                <ScoreSlider
                  minValue={filters.min_score ?? -1}
                  maxValue={filters.max_score ?? 100}
                  onCommit={(minScore, maxScore) => update({ min_score: minScore, max_score: maxScore })}
                />
              </div>
            </div>
          </Section>

          {/* KATMAN 2: DEĞERLENDİRME & KARİYER OPS ARKETİPLERİ */}
          {(Object.keys(facets.recommendations ?? {}).length > 0 ||
            Object.keys(facets.archetypes ?? {}).length > 0) && (
            <Section title="Kariyer analizi & rol tipi">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
                {Object.keys(facets.recommendations ?? {}).length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="label-caps mr-1 text-secondary">Karar</span>
                    {chips(facets.recommendations, filters.recommendation, RECOMMENDATION_LABELS, "recommendation")}
                  </div>
                )}
                {Object.keys(facets.archetypes ?? {}).length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="label-caps mr-1 text-secondary">Rol tipi</span>
                    {chips(facets.archetypes, filters.archetype, ARCHETYPE_LABELS, "archetype")}
                  </div>
                )}
              </div>
            </Section>
          )}
        </>
      )}

      {/* KATMAN 3: ÇALIŞMA BİÇİMİ, KONUM VE TARİH */}
      <Section title={filters.section === "jobs" ? "Çalışma biçimi & konum" : "Kurum & tarih"}>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {filters.section === "jobs" && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="label-caps mr-1">Konum</span>
              {chips(
                facets.regions,
                filters.region,
                { TR: "Türkiye", EU: "Avrupa", OTHER: "Diğer", UNKNOWN: "Konum bilinmiyor" },
                "region",
              )}
            </div>
          )}
          {filters.section === "jobs" && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="label-caps mr-1">Çalışma biçimi</span>
              {chips(facets.remote, filters.remote, REMOTE_LABELS, "remote")}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <span className="label-caps mr-1">Kaynak</span>
            <FilterChip
              label="✍️ Manuel Eklenenler"
              count={facets.sources?.manual}
              active={filters.source === "manual"}
              onClick={() => update({ source: filters.source === "manual" ? "" : "manual" })}
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
          {filters.section === "announcements" && (
            <>
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
                  .sort((a, b) => Number(b) - Number(a))
                  .map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
              </Select>
            </>
          )}
        </div>
      </Section>

      {/* KATMAN 4: DURUM VE SIRALAMA */}
      <Section title="Durum & sıralama">
        <div className="flex flex-wrap items-center gap-2">
          {chips(
            facets.statuses,
            filters.status,
            Object.fromEntries(STATUSES.map((s) => [s, statusLabel(s)])),
            "status",
          )}
          <Select
            ariaLabel="Sıralama"
            value={filters.sort}
            onChange={(sort) => update({ sort: sort as OpportunityBrowseFilters["sort"] })}
          >
            {filters.section === "jobs" && (
              <>
                <option value="score">Skor: yüksekten düşüğe</option>
                <option value="skill_match">CV eşleşmesi: en yüksek uyum</option>
                <option value="score_asc">Skor: düşükten yükseğe</option>
              </>
            )}
            <option value="newest">En yeni</option>
            <option value="oldest">En eski</option>
            <option value="deadline">Son tarihe göre</option>
          </Select>
        </div>
      </Section>
    </div>
  );
}
