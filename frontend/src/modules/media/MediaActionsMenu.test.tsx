// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MediaActionsMenu } from "./MediaActionsMenu";

const item = {
  id: "media-1",
  title: "Dune",
  kind: "movie",
  meta: {},
  provider: null,
  provider_id: null,
  provider_ids: {},
};

describe("MediaActionsMenu", () => {
  afterEach(cleanup);

  it("opens relevant links, closes on Escape, and restores trigger focus", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);

    const trigger = screen.getByRole("button", { name: "Dune işlemleri" });
    await user.click(trigger);
    const menu = screen.getByRole("group", { name: "Dune işlemleri menüsü" });
    expect(screen.queryByRole("menu")).toBeNull();
    for (const name of ["TMDB", "IMDb", "Rotten Tomatoes", "Letterboxd"]) {
      expect(within(menu).getByRole("link", { name: new RegExp(`^${name}`) })).toBeTruthy();
    }

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("group", { name: "Dune işlemleri menüsü" })).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("closes when a pointer event happens outside the menu", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    expect(screen.getByRole("group", { name: "Dune işlemleri menüsü" })).toBeTruthy();
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("group", { name: "Dune işlemleri menüsü" })).toBeNull();
  });

  it("disables the trash action while an item mutation is pending", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled />);

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    expect((screen.getByRole("button", { name: "Çöpe taşı" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
