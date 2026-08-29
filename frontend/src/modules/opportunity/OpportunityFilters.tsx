import { Button, Field, NumberInput, Select, Section } from "@/core/ui";
import { sourceLabel } from "@/core/labels";
import { FilterChip } from "./OpportunityList";
import { JOB_CATEGORY_LABELS, STATUSES, statusLabel } from "./labels";
import type { OpportunityBrowseFilters } from "./opportunityBrowse";

interface Props {
  filters: OpportunityBrowseFilters;
  facets: Record<string, Record<string, number>>;
  onChange: (next: OpportunityBrowseFilters) => void;
}

const SCORE_PRESETS = [
  { label: "70–100", min: 70, max: 100 },
  { label: "40–69", min: 40, max: 69.9 },
  { label: "0–39", min: 0, max: 39.9 },
  { label: "Elendi", min: -1, max: -1 },
] as const;

function clampScore(value: number): number {
  return Math.max(-1, Math.min(100, value));
}

export function OpportunityFilters({ filters, facets, onChange }: Props) {
  const remoteLabels: Record<string, string> = {
    remote: "Uzaktan",
    hybrid: "Hibrit",
    onsite: "Ofis",
    office: "Ofis",
    unknown: "Belirsiz",
  };
  const update = (changes: Partial<OpportunityBrowseFilters>) => onChange({ ...filters, ...changes, offset: 0 });
  const scoreFilterActive = filters.min_score !== undefined || filters.max_score !== undefined;
  const chips = (
    values: Record<string, number> | undefined,
    selected: string | undefined,
    labels: Record<string, string>,
    key: "category" | "status" | "source" | "region" | "remote" | "announcement_source",
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

      {filters.section === "jobs" && (
        <Section title="İş alanı">
          <div className="flex flex-wrap gap-2">
            {chips(facets.categories, filters.category, JOB_CATEGORY_LABELS, "category")}
          </div>
        </Section>
      )}

      {filters.section === "jobs" && (
        <Section
          title="Uyum skoru"
          hint={scoreFilterActive ? `${filters.min_score ?? -1}–${filters.max_score ?? 100}` : "Tüm skorlar"}
          action={
            scoreFilterActive ? (
              <Button size="sm" variant="ghost" onClick={() => update({ min_score: undefined, max_score: undefined })}>
                Temizle
              </Button>
            ) : undefined
          }
        >
          <div className="flex flex-wrap items-end gap-2">
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
            <Field label="Minimum skor" className="w-32">
              <NumberInput
                ariaLabel="Minimum skor"
                value={filters.min_score ?? -1}
                min={-1}
                max={100}
                step={0.1}
                className="w-full"
                onChange={(value) => {
                  const minScore = clampScore(value);
                  update({
                    min_score: minScore,
                    max_score:
                      filters.max_score !== undefined && minScore > filters.max_score ? minScore : filters.max_score,
                  });
                }}
              />
            </Field>
            <Field label="Maksimum skor" className="w-32">
              <NumberInput
                ariaLabel="Maksimum skor"
                value={filters.max_score ?? 100}
                min={-1}
                max={100}
                step={0.1}
                className="w-full"
                onChange={(value) => {
                  const maxScore = clampScore(value);
                  update({
                    min_score:
                      filters.min_score !== undefined && maxScore < filters.min_score ? maxScore : filters.min_score,
                    max_score: maxScore,
                  });
                }}
              />
            </Field>
          </div>
        </Section>
      )}

      <Section title={filters.section === "jobs" ? "Çalışma biçimi & konum" : "Kurum & tarih"}>
        <div className="flex flex-wrap items-center gap-2">
          {filters.section === "jobs" &&
            chips(
              facets.regions,
              filters.region,
              { TR: "Türkiye", EU: "Avrupa", OTHER: "Diğer", UNKNOWN: "Belirsiz" },
              "region",
            )}
          {filters.section === "jobs" && chips(facets.remote, filters.remote, remoteLabels, "remote")}
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
