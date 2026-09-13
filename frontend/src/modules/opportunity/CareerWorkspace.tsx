import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Tabs } from "@/core/ui";
import type { OpportunityLifecycle } from "@/core/types";
import { CareerStoryBank } from "./CareerStoryBank";
import { CareerConnectionsPanel } from "./CareerConnectionsPanel";
import { CompanyResearchPanel } from "./CompanyResearchPanel";
import { InterviewPrepPanel } from "./InterviewPrepPanel";
import { CoverLetterPanel } from "./CoverLetterPanel";
import { JobhunterSettings } from "./JobhunterSettings";

type CareerTab = "stories" | "connections" | "company" | "interview" | "cover" | "settings";

const TABS = [
  { id: "stories", label: "Hikâye bankası" },
  { id: "connections", label: "Bağlantı ağı" },
  { id: "company", label: "Şirket araştırması" },
  { id: "interview", label: "Mülakat hazırlığı" },
  { id: "cover", label: "Ön yazı" },
  { id: "settings", label: "Jobhunter ayarları" },
] as const;

/**
 * Kariyer çalışma alanı: altı sekmeli, tamamen yerel hazırlık yüzeyi.
 * Derin bağlar (`focusStoryId`, `focusConnectionId`) ilgili sekmeyi açar ve
 * kaydı seçer/vurgular; hikâye düzenleyicisi yalnızca istendiğinde görünür.
 */
export function CareerWorkspace({
  focusStoryId,
  focusConnectionId,
}: {
  focusStoryId: string | null;
  focusConnectionId: string | null;
}) {
  const [tab, setTab] = useState<CareerTab>(() =>
    focusConnectionId ? "connections" : focusStoryId ? "stories" : "stories",
  );
  const { data: lifecycle } = useQuery<OpportunityLifecycle>({
    queryKey: ["opportunity-lifecycle"],
    queryFn: () => api.get<OpportunityLifecycle>("/opportunities/lifecycle"),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (focusStoryId) setTab("stories");
  }, [focusStoryId]);
  useEffect(() => {
    if (focusConnectionId) setTab("connections");
  }, [focusConnectionId]);

  const jobKinds = lifecycle?.job_kinds ?? [];

  return (
    <div className="space-y-3">
      {/* Sekme şeridi artık `Tabs` içinde yatay kayar (dar ekranda taşmaz);
          etiketler kırpılmaz, erişilebilir adlar rozetle birlikte verilir. */}
      <Tabs value={tab} onChange={setTab} items={[...TABS]} ariaLabel="Kariyer çalışma alanı sekmeleri" />
      {tab === "stories" && <CareerStoryBank focusId={focusStoryId} />}
      {tab === "connections" && <CareerConnectionsPanel focusId={focusConnectionId} />}
      {tab === "company" && <CompanyResearchPanel jobKinds={jobKinds} />}
      {tab === "interview" && <InterviewPrepPanel />}
      {tab === "cover" && <CoverLetterPanel />}
      {tab === "settings" && <JobhunterSettings />}
    </div>
  );
}
