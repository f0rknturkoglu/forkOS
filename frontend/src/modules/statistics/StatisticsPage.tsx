import { PageFrame } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { StatisticsWidget } from "./StatisticsWidget";

/** Istatistik sayfasi -- widget'in genis gorunumu (Today'dekiyle ayni veri). */
export function StatisticsPage() {
  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader eyebrow="Sistem" title="İstatistikler" hint="Kişisel ritim özeti" />
        <WorkspaceScrollArea className="p-3">
          <StatisticsWidget />
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
