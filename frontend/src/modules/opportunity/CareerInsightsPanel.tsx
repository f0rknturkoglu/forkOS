import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button, Chip, Empty, Select, Section, Spinner } from "@/core/ui";
import type { components } from "@/generated/api-schema";

type Snapshot = components["schemas"]["CareerAnalyticsSnapshot"];

const metricLabels: Record<string, string> = {
  discovered: "Keşfedilen",
  prepared: "Paket üretilen",
  applied: "Başvurulan",
  reply: "Yanıt kaydı",
  recruiter_screen: "İlk görüşme",
  interview: "Görüşme aşaması",
  offer: "Teklif",
  rejected: "Ret",
  withdrawn: "Geri çekilen",
  applied_to_interview: "Başvurudan görüşmeye",
  applied_to_offer: "Başvurudan teklife",
  prepared_to_applied: "Paketten başvuruya",
  applied_to_rejected: "Başvurudan rete",
  preparing_to_applied: "Hazırlıktan başvuruya",
  applied_to_withdrawn: "Başvurudan geri çekmeye",
};
function sampleLabel(status: string) {
  return status === "insufficient_sample"
    ? "Yetersiz örnek"
    : status === "incomplete_history"
      ? "Eksik geçmiş"
      : "Betimsel ilişki";
}

export function CareerInsightsPanel() {
  const [days, setDays] = useState("30");
  const query = useQuery({
    queryKey: ["career-insights", days],
    queryFn: () => api.get<Snapshot>(`/career/insights?days=${days}&minimum=3`),
    staleTime: 60_000,
  });
  return (
    <Section title="Kariyer içgörüleri" hint="Yerel, betimsel; korelasyon neden değildir">
      <Select value={days} onChange={setDays} ariaLabel="Analiz dönemi">
        <option value="30">Son 30 gün keşfedilenler</option>
        <option value="90">Son 90 gün keşfedilenler</option>
        <option value="365">Son yıl keşfedilenler</option>
      </Select>
      {query.isLoading && <Spinner label="Analitik hesaplanıyor…" />}
      {query.isError && (
        <div role="alert">
          <p className="text-meta text-danger">{query.error.message}</p>
          <Button onClick={() => void query.refetch()}>Tekrar dene</Button>
        </div>
      )}
      {query.data && (
        <div className="mt-3 stack-y-4">
          {!query.data.population && <Empty title="Bu dönemde keşfedilmiş ilan yok">Dönemi genişletebilirsin.</Empty>}
          <p className="text-meta text-muted">
            Örnek: {query.data.population}; en az {query.data.minimum_sample}. Dönem keşif tarihine göre, sonuçlar
            güncel gözlemdir.
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(query.data.funnel).map(([stage, count]) => (
              <Chip key={stage} tone="neutral">
                {metricLabels[stage] || stage}: {count}
              </Chip>
            ))}
          </div>
          {Object.entries(query.data.conversions).map(([name, rate]) => (
            <p key={name} className="text-meta text-secondary">
              {metricLabels[name] || name}: {rate.numerator}/{rate.denominator} ·{" "}
              {rate.rate == null ? sampleLabel(rate.status) : `${(rate.rate * 100).toFixed(1)}%`}
            </p>
          ))}
          <h3 className="text-body font-semibold text-primary">Tekrarlayan beceri sinyalleri</h3>
          {!query.data.skill_gaps.length && (
            <p className="text-meta text-muted">Güncel değerlendirmelerden beceri sinyali yok.</p>
          )}
          {query.data.skill_gaps.map((g) => (
            <p key={g.requirement} className="text-meta text-secondary">
              {g.requirement}: güncel değerlendirmede {g.opportunities_seen}/{query.data.evaluated_population}; güçlü{" "}
              {g.strong_count}, kısmi {g.partial_count}, eksik {g.missing_count}, bilinmiyor {g.unknown_count} ·{" "}
              {sampleLabel(g.confidence)}
            </p>
          ))}
          <h3 className="text-body font-semibold text-primary">Kaynaklar ve coğrafya</h3>
          {[...query.data.source_performance, ...query.data.geography].map((c) => (
            <p key={`${c.dimension}:${c.value}`} className="text-meta text-secondary">
              {c.dimension} / {c.value}: n={c.sample_size}, başvuru {c.counts.applied || 0}, görüşme{" "}
              {c.counts.interview || 0} · {sampleLabel(c.status)}
            </p>
          ))}
          <h3 className="text-body font-semibold text-primary">Sonuçlar ve kalibrasyon</h3>
          {Object.entries(query.data.durations ?? {}).map(([name, duration]) => (
            <p key={name} className="text-meta text-secondary">
              {metricLabels[name] || name}: n={duration.sample_size}; medyan{" "}
              {duration.median_days == null ? "yetersiz veri" : `${Number(duration.median_days).toFixed(1)} gün`}
            </p>
          ))}
          <p className="text-meta text-secondary">
            {query.data.rejection_patterns.length} ret gözlemi; {query.data.calibration.length} puan/sonuç
            karşılaştırması. Puan ağırlıkları değişmedi.
          </p>
          {query.data.rejection_patterns.slice(0, 10).map((r) => (
            <p key={String(r.opportunity_id)} className="text-meta text-secondary">
              {String(r.reason || "Ret nedeni bilinmiyor")} ·{" "}
              {r.classification === "explicit_reason"
                ? "Bildirilen işveren alıntısı; bağımsız doğrulanmadı"
                : r.classification === "user_entered_reason"
                  ? "Kullanıcının bildirdiği neden"
                  : "Bilinmiyor"}
            </p>
          ))}
          {query.data.calibration.slice(0, 5).map((c) => (
            <p key={String(c.opportunity_id)} className="text-meta text-secondary">
              Kural puanı: {String(c.rule_score ?? "bilinmiyor")}; gözlenen sonuçlar:{" "}
              {Array.isArray(c.observed_outcomes)
                ? c.observed_outcomes.map((o) => metricLabels[String(o)] || String(o)).join(", ")
                : "bilinmiyor"}
              . Tarihsel puan snapshot'ı olmadığında yalnızca mevcut kayıt karşılaştırılır.
            </p>
          ))}
          <p className="text-meta text-muted">
            {query.data.lineage?.filter((l) => l.base_cv_document_id).length || 0} kayıtta temel CV sürümü izleniyor;
            CV'nin sonucu nedenlediği iddia edilmez.
          </p>
          {Object.entries(query.data.briefing).map(([key, value]) => (
            <p key={key} className="text-meta text-secondary">
              {value}
            </p>
          ))}
          {query.data.confidence_notes.map((note) => (
            <p key={note} className="text-meta text-muted">
              {note}
            </p>
          ))}
        </div>
      )}
    </Section>
  );
}
