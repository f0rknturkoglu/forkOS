export function GoalCoachingFacts({ value, label = "Bu yanıtın kayıtlı durumu" }: { value: unknown; label?: string }) {
  if (!value || typeof value !== "object") return null;
  const facts = value as Record<string, unknown>;
  const titles = (key: string) =>
    Array.isArray(facts[key]) ? (facts[key] as unknown[]).filter((s): s is string => typeof s === "string") : [];
  return (
    <section aria-label={label} className="mb-3 border-b border-subtle pb-3 stack-y-2">
      <p className="text-meta text-muted">{label}</p>
      <p className="text-body">
        Çalışma ilerlemesi: {typeof facts.percent === "number" ? `%${facts.percent}` : "Henüz bilinmiyor"}
        {typeof facts.completed === "number" && typeof facts.total === "number" && (
          <span>
            {" "}
            · {facts.completed}/{facts.total} görev tamamlandı
          </span>
        )}
      </p>
      <p className="text-meta text-secondary">
        Gerçek sonuç: {typeof facts.outcome_percent === "number" ? `%${facts.outcome_percent}` : "Henüz ölçülmedi"}
        {" · Hazırlık ilerlemesinden ayrı ölçülür."}
      </p>
      {titles("remaining").length > 0 && (
        <p className="text-meta text-secondary">Bekleyen: {titles("remaining").join(" · ")}</p>
      )}
      {titles("actions").length > 0 && (
        <p className="text-meta text-secondary">Sıradaki öneri: {titles("actions").join(" · ")}</p>
      )}
      {facts.truncated === true && (
        <p className="text-meta text-warn">Bu değerlendirme kaydedilmiş çalışmaların sınırlı bir bölümünü içeriyor.</p>
      )}
    </section>
  );
}
