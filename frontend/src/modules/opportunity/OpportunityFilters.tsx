import { Select, Section } from "@/core/ui";
import { sourceLabel } from "@/core/labels";
import { FilterChip } from "./OpportunityList";
import { JOB_CATEGORY_LABELS, STATUSES, statusLabel } from "./labels";
import type { OpportunityBrowseFilters } from "./opportunityBrowse";

interface Props {
  filters: OpportunityBrowseFilters;
  facets: Record<string, Record<string, number>>;
  onChange: (next: OpportunityBrowseFilters) => void;
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
            {filters.section === "jobs" && <option value="score">En uygun</option>}
            <option value="newest">En yeni</option>
            <option value="oldest">En eski</option>
            <option value="deadline">Son tarihe göre</option>
          </Select>
        </div>
      </Section>
    </div>
  );
}
