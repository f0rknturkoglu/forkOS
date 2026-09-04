import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  Workspace,
  WorkspaceInspectorContent,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "./Workspace";

describe("workspace primitives", () => {
  it("renders rail, main pane and inspector in one shared surface", () => {
    const markup = renderToStaticMarkup(
      <Workspace
        rail={
          <WorkspaceRailContent>
            <WorkspaceRailGroup label="Görünümler">
              <WorkspaceRailButton label="Tümü" count={4} active onClick={() => undefined} />
            </WorkspaceRailGroup>
          </WorkspaceRailContent>
        }
        inspector={<WorkspaceInspectorContent title="Ayrıntılar">Seçim</WorkspaceInspectorContent>}
      >
        <WorkspacePaneHeader title="Kayıtlar" hint="4 kayıt" />
        <WorkspaceScrollArea>Liste</WorkspaceScrollArea>
      </Workspace>,
    );

    expect(markup).toContain("Görünümler");
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain("Kayıtlar");
    expect(markup).toContain("Ayrıntılar");
    expect(markup).toContain("xl:grid-cols-workspace-three");
  });

  it("can defer the rail split for dense workspaces", () => {
    const markup = renderToStaticMarkup(
      <Workspace rail={<div>Backlog</div>} railAt="lg">
        Takvim
      </Workspace>,
    );

    expect(markup).toContain("lg:grid-cols-workspace-rail");
    expect(markup).toContain("lg:border-r");
  });

  it("supports a wide rail and a wrapping pane title", () => {
    const markup = renderToStaticMarkup(
      <Workspace rail={<div>Konu ağacı</div>} railAt="lg" railWidth="wide">
        <WorkspacePaneHeader title="Uzun bir konu başlığı" wrapTitle />
      </Workspace>,
    );

    expect(markup).toContain("lg:grid-cols-workspace-wide-rail");
    expect(markup).toContain('class="break-words text-heading text-primary"');
  });
});
