import { WIDGETS } from "./widgets";
import { PageFrame } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";

/** Genel saglik dashboard'u -- widget listesinden beslenir. */
export function HealthPage() {
  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader eyebrow="Sistem" title="Sistem Durumu" hint="Kaynaklar, beslemeler ve yedekler" />
        <WorkspaceScrollArea className="p-3">
          <div className="grid items-start gap-4 xl:grid-cols-2">
            {WIDGETS.map(({ name, component: Widget }) => (
              <Widget key={name} />
            ))}
          </div>
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
