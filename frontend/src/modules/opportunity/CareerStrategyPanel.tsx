import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button, Chip, Empty, Section, Spinner } from "@/core/ui";
import type { components } from "@/generated/api-schema";
import { CareerGoalsPanel } from "./CareerGoalsPanel";
import { CareerProposalsPanel } from "./CareerProposalsPanel";

type Strategy = components["schemas"]["CareerStrategySnapshot"];

export function CareerStrategyPanel() {
  const query = useQuery({
    queryKey: ["career-strategy"],
    queryFn: () => api.get<Strategy>("/career/strategy?days=90&minimum=3"),
    staleTime: 60_000,
  });

  return (
    <Section title="Kariyer stratejisi" hint="Özet okunur; öneriler yalnızca açık onayla kanonik kayda dönüşür">
      {query.isLoading && <Spinner label="Strateji kanıtları değerlendiriliyor…" />}
      {query.isError && (
        <div role="alert">
          <p className="text-meta text-danger">Strateji yüklenemedi: {query.error.message}</p>
          <Button onClick={() => void query.refetch()}>Tekrar dene</Button>
        </div>
      )}
      {query.data && (
        <div className="space-y-5">
          <p className="text-body text-primary">{query.data.summary}</p>
          <p className="text-meta text-secondary">Son değerlendirmeden beri: {query.data.what_changed}</p>
          <div>
            <h3 className="text-body font-semibold text-primary">Kayıtlı uzun vadeli yön</h3>
            {query.data.existing_goals.length ? (
              query.data.existing_goals.map((goal, index) => (
                <p key={goal.evidence_refs?.[0] ?? index} className="text-meta text-secondary">
                  {goal.title} · {goal.caveat}
                </p>
              ))
            ) : (
              <p className="text-meta text-muted">Etkin H2 hedef hafızası bulunamadı.</p>
            )}
          </div>
          <p className="text-meta text-muted">
            Dönem: {new Date(query.data.period.start).toLocaleDateString("tr-TR")} –{" "}
            {new Date(query.data.period.end).toLocaleDateString("tr-TR")}; kanıt revizyonu{" "}
            {query.data.evidence_revision.slice(0, 16)}
          </p>
          <div>
            <h3 className="text-body font-semibold text-primary">Şimdi ne yapmalıyım?</h3>
            {query.data.primary_action ? (
              <div className="space-y-2">
                <p className="text-body text-primary">{query.data.primary_action.title}</p>
                <p className="text-meta text-secondary">{query.data.primary_action.why}</p>
                {query.data.alternatives.map((action) => (
                  <p key={action.title} className="text-meta text-secondary">
                    Alternatif: {action.title} — {action.why}
                  </p>
                ))}
              </div>
            ) : (
              <Empty title="Öncelikli eylem için kayıt yok">
                Yakın tarihli görev veya aktif proje adımı belirlenmemiş.
              </Empty>
            )}
          </div>
          <div>
            <h3 className="text-body font-semibold text-primary">Kanıta dayalı sinyaller</h3>
            {query.data.signals.length === 0 && (
              <p className="text-meta text-muted">Bu dönemde yeterli örnekli tekrarlayan açık yok.</p>
            )}
            {query.data.signals.slice(0, 3).map((signal) => (
              <div key={signal.title} className="space-y-1 py-2">
                <p className="text-body text-primary">{signal.title}</p>
                <div className="flex flex-wrap gap-2">
                  <Chip tone="neutral">n={signal.sample_size}</Chip>
                  <Chip tone="neutral">{signal.confidence === "medium" ? "Orta güven" : "Düşük güven"}</Chip>
                </div>
                <p className="text-meta text-muted">{signal.caveat}</p>
              </div>
            ))}
          </div>
          <div>
            <h3 className="text-body font-semibold text-primary">Hedef adımlarının tamamlanması</h3>
            {query.data.goal_progress.length === 0 && (
              <p className="text-meta text-muted">Ölçülebilir operasyonel hedef kaydı yok.</p>
            )}
            {query.data.goal_progress.map((item) => (
              <p key={item.goal_id} className="text-meta text-secondary">
                {item.title}: {item.completed_milestones}/{item.milestone_count}
                {item.progress_percent === null ? " · yüzde için payda yok" : ` · %${item.progress_percent}`}
                {item.changed_since_last_review ? ` · ${item.changed_since_last_review}` : ""}
              </p>
            ))}
          </div>
          <div>
            <h3 className="text-body font-semibold text-primary">Proje kilometre taşları</h3>
            {query.data.project_progress.length === 0 && (
              <p className="text-meta text-muted">Proje kilometre taşı kaydı yok.</p>
            )}
            {query.data.project_progress.map((item) => (
              <p key={item.project_id} className="text-meta text-secondary">
                {item.title}: {item.completed_milestones}/{item.milestone_count}
                {item.progress_percent === null ? " · yüzde için payda yok" : ` · %${item.progress_percent}`}
              </p>
            ))}
          </div>
          <CareerProposalsPanel />
          <CareerGoalsPanel />
          <details>
            <summary className="cursor-pointer text-body text-primary">Kanıt ve sınırlar</summary>
            {[...query.data.uncertainties, ...query.data.audit].map((note) => (
              <p key={note} className="mt-2 text-meta text-muted">
                {note}
              </p>
            ))}
          </details>
        </div>
      )}
    </Section>
  );
}
