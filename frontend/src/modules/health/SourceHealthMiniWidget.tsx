import { useQuery } from "@tanstack/react-query";
import { useSourceHealth } from "@/core/runtimeQueries";
import { AlertTriangle } from "lucide-react";
import { api } from "@/core/api";
import { Empty, Section } from "@/core/ui";
import type { SourceHealth } from "@/core/types";

/** Kaynak sagligi ozeti: yalnizca bozuk kaynak varsa gorunur (StatusLed ust seritte). */
export function SourceHealthMiniWidget() {
  // Kabuktaki paylasilan saglik sorgusu: cekim surerken hizlanir, bosta seyrek.
  const { data = [] } = useSourceHealth();
  const broken = data.filter((run) => run.status === "error" || run.status === "empty");
  const names = broken
    .slice(0, 3)
    .map((run) => run.source)
    .join(", ");
  return (
    <Section title="Kaynak sağlığı">
      {broken.length === 0 ? (
        <Empty>Kaynaklar sağlıklı.</Empty>
      ) : (
        <a href="#/health" className="flex items-center gap-2 text-meta text-danger hover:underline">
          <AlertTriangle size={13} className="shrink-0" />
          {broken.length} kaynak hata veriyor{names ? ` (${names}${broken.length > 3 ? "…" : ""})` : ""}
        </a>
      )}
    </Section>
  );
}
