import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button } from "@/core/ui";
import { navigate } from "@/app/router";
import type { components } from "@/generated/api-schema";
export function CareerGoalsPanel() {
  const goals = useQuery({
    queryKey: ["career-goals"],
    queryFn: () => api.get<components["schemas"]["GoalOut"][]>("/goals"),
  });
  return (
    <div className="space-y-2 border-t border-subtle pt-4">
      <h3 className="text-body font-semibold">Hedefler</h3>
      <p className="text-meta text-muted">
        {goals.isError
          ? "Hedef özeti yüklenemedi."
          : goals.isPending
            ? "Hedefler yükleniyor…"
            : `${goals.data.filter((g) => g.status === "active").length} aktif hedef.`}{" "}
        Sonuç ölçümü, plan ve hedef adımları Hedefler alanında.
      </p>
      <Button onClick={() => navigate("/goals")}>Hedefleri aç</Button>
    </div>
  );
}
