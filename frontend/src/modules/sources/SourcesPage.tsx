/**
 * `/sources` — Sistem alanındaki Kaynaklar rotası.
 *
 * Yüzey TEK: `SourcesWorkspace` burada "system" çerçevesiyle, Kariyer >
 * Kaynaklar sekmesinde "career" çerçevesiyle aynı bileşeni kullanır. Bu dosya
 * yalnız kabuğu (sayfa başlığı), kapsam ayrımını ve derin bağlantıları taşır.
 *
 * Derin bağlantılar:
 *   `?filter=problems` (ya da `?problem=1`) → yalnızca sorunlular süzgeci açık,
 *   `?source=<id>` → ilgili kaynak satırı vurgulanır ve görünüme kaydırılır.
 */
import { useHashRoute } from "@/app/router";
import { PageFrame } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { SourceSyncBatchHistory } from "./SourceSyncBatchHistory";
import { SourcesWorkspace } from "./SourcesWorkspace";

export function SourcesPage() {
  const route = useHashRoute();
  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Sistem"
          title="Kaynak Durumu"
          hint="Katalog, sağlık, koşu geçmişi ve disk önbelleği"
        />
        <WorkspaceScrollArea className="space-y-4 p-4 sm:p-6">
          <SourcesWorkspace
            framing="system"
            initialProblemOnly={route.params.get("filter") === "problems" || route.params.get("problem") === "1"}
            focusSource={route.params.get("source")}
          />
          <SourceSyncBatchHistory />
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
