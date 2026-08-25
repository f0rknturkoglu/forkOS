// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  it("opens a labelled ARIA menu, relates it to the trigger, and focuses its first item", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);

    const trigger = screen.getByRole("button", { name: "Dune işlemleri" });
    await user.click(trigger);
    const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
    expect(trigger.getAttribute("aria-haspopup")).toBe("menu");
    expect(trigger.getAttribute("aria-controls")).toBe(menu.id);
    for (const name of ["TMDB", "IMDb", "Rotten Tomatoes", "Letterboxd"]) {
      expect(within(menu).getByRole("menuitem", { name: new RegExp(`^${name}`) })).toBeTruthy();
    }
    expect(within(menu).getByRole("menuitem", { name: "Çöpe taşı" })).toBeTruthy();
    expect(document.activeElement).toBe(within(menu).getByRole("menuitem", { name: /^TMDB/ }));
  });

  it("wraps Arrow keys and honors Home and End for enabled menuitems", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
    const tmdb = within(menu).getByRole("menuitem", { name: /^TMDB/ });
    const letterboxd = within(menu).getByRole("menuitem", { name: /^Letterboxd/ });
    const trash = within(menu).getByRole("menuitem", { name: "Çöpe taşı" });

    fireEvent.keyDown(tmdb, { key: "ArrowDown" });
    expect(document.activeElement).toBe(letterboxd);
    fireEvent.keyDown(letterboxd, { key: "ArrowUp" });
    expect(document.activeElement).toBe(tmdb);
    fireEvent.keyDown(tmdb, { key: "ArrowUp" });
    expect(document.activeElement).toBe(trash);
    fireEvent.keyDown(trash, { key: "Home" });
    expect(document.activeElement).toBe(tmdb);
    fireEvent.keyDown(tmdb, { key: "End" });
    expect(document.activeElement).toBe(trash);
  });

  it("closes on Escape and restores trigger focus", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);

    const trigger = screen.getByRole("button", { name: "Dune işlemleri" });
    await user.click(trigger);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu", { name: "Dune işlemleri menüsü" })).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("closes when a pointer event happens outside the menu", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    expect(screen.getByRole("menu", { name: "Dune işlemleri menüsü" })).toBeTruthy();
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("menu", { name: "Dune işlemleri menüsü" })).toBeNull();
  });

  it("disables the trash action while an item mutation is pending", async () => {
    const user = userEvent.setup();
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled />);

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
    const trash = within(menu).getByRole("menuitem", { name: "Çöpe taşı" }) as HTMLButtonElement;
    expect(trash.disabled).toBe(true);
    fireEvent.keyDown(document.activeElement!, { key: "End" });
    expect(document.activeElement).toBe(within(menu).getByRole("menuitem", { name: /^Rotten Tomatoes/ }));
  });

  it("keeps a first-column menu inside a narrow viewport", async () => {
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);
    const trigger = screen.getByRole("button", { name: "Dune işlemleri" });
    vi.spyOn(trigger, "getBoundingClientRect").mockReturnValue({
      x: 2, y: 24, top: 24, left: 2, right: 34, bottom: 56, width: 32, height: 32,
      toJSON: () => ({}),
    });

    fireEvent.click(trigger);
    const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
    await waitFor(() => expect(menu.className).toContain("fixed"));
    const left = Number.parseFloat(menu.style.left);
    const width = Number.parseFloat(menu.style.width);
    expect(left).toBeGreaterThanOrEqual(8);
    expect(left + width).toBeLessThanOrEqual(375 - 8);
    Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth });
  });
});
