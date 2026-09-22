import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  Workspace,
  WorkspaceBody,
  WorkspaceInspectorContent,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
  WorkspaceToolbar,
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

  it("renders page-local toolbar with left and right action slots", () => {
    const markup = renderToStaticMarkup(
      <WorkspaceToolbar
        left={<span>Filtreler</span>}
        right={<button type="button">Yeni Ekle</button>}
      />,
    );

    expect(markup).toContain('role="toolbar"');
    expect(markup).toContain("Filtreler");
    expect(markup).toContain("Yeni Ekle");
  });

  it("supports bounded vs full-width workspace body modes", () => {
    const boundedMarkup = renderToStaticMarkup(
      <WorkspaceBody mode="bounded">
        <div>İçerik</div>
      </WorkspaceBody>,
    );
    expect(boundedMarkup).toContain("max-w-5xl");
    expect(boundedMarkup).toContain("data-workspace-body");

    const fullMarkup = renderToStaticMarkup(
      <WorkspaceBody mode="full">
        <div>Tablo</div>
      </WorkspaceBody>,
    );
    expect(fullMarkup).toContain("w-full");
    expect(fullMarkup).not.toContain("max-w-5xl");
    expect(fullMarkup).toContain("data-workspace-body");
  });

  it("WorkspaceRailButton renders icon, label and count", () => {
    const markup = renderToStaticMarkup(
      <WorkspaceRailButton
        label="Proje A"
        count="3 gün önce · aktif"
        active
        icon={<span className="h-2 w-2 rounded-full bg-ok" />}
        onClick={() => undefined}
      />,
    );
    expect(markup).toContain("Proje A");
    expect(markup).toContain("3 gün önce · aktif");
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain("bg-ok");
  });
});
