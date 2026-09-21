/**
 * `/sources` — Sistem alanındaki Kaynaklar rotası.
 *
 * Yüzey TEK: `SourcesWorkspace` burada "system" çerçevesiyle, Kariyer >
 * Kaynaklar sekmesinde "career" çerçevesiyle aynı bileşeni kullanır. Bu dosya
 * yalnız kabuğu (sayfa başlığı), kapsam ayrımını ve derin bağlantıları taşır.
 *
 * Kapsam: `?scope=media` yalnız çekim ilerlemesini ve parti geçmişini gösterir;
 * iş sınıfı, kapsam matrisi ve duyuru türü kariyer yüzeyine aittir.
 *
 * Derin bağlantılar:
 *   `?filter=problems` (ya da `?problem=1`) → yalnızca sorunlular süzgeci açık,
 *   `?source=<id>` → ilgili kaynak satırı vurgulanır ve görünüme kaydırılır.
 */
import { useHashRoute } from "@/app/router";
import { PageFrame } from "@/core/ui";
import { SyncProgress, type SourceSyncScope } from "@/core/SyncProgress";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { SourceSyncBatchHistory } from "./SourceSyncBatchHistory";
import { SourcesWorkspace } from "./SourcesWorkspace";

export function SourcesPage() {
  const route = useHashRoute();
  const scope: SourceSyncScope = route.params.get("scope") === "media" ? "media" : "opportunity";

  if (scope === "media") {
    return (
      <PageFrame>
        <Workspace>
          <WorkspacePaneHeader
            eyebrow="Sistem"
            title="Medya Kaynak Durumu"
            hint="Yalnız medya sağlayıcılarının çekim ilerlemesi ve parti geçmişi"
          />
          <WorkspaceScrollArea className="space-y-4 p-3">
            <SyncProgress scope="media" />
            <SourceSyncBatchHistory scope="media" />
          </WorkspaceScrollArea>
        </Workspace>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Sistem"
          title="Kaynak Durumu"
          hint="Katalog, sağlık, koşu geçmişi ve disk önbelleği"
        />
        <WorkspaceScrollArea className="space-y-4 p-3">
          <SourcesWorkspace
            framing="system"
            initialProblemOnly={route.params.get("filter") === "problems" || route.params.get("problem") === "1"}
            focusSource={route.params.get("source")}
          />
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
