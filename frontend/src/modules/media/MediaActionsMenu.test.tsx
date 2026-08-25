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

  it("restores trigger focus after selecting an action", async () => {
    const user = userEvent.setup();
    const onTrash = vi.fn();
    render(<MediaActionsMenu item={item} onTrash={onTrash} disabled={false} />);

    const trigger = screen.getByRole("button", { name: "Dune işlemleri" });
    await user.click(trigger);
    await user.click(screen.getByRole("menuitem", { name: "Çöpe taşı" }));

    expect(onTrash).toHaveBeenCalledWith(item);
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

  it("flips above a bottom-edge trigger when the menu fits there", async () => {
    const originalHeight = window.innerHeight;
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 640 });
    const naturalHeight = vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.getAttribute("role") === "menu" ? 220 : 0;
    });
    const rect = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.getAttribute("role") === "menu") {
        return { x: 0, y: 0, top: 0, left: 0, right: 208, bottom: 220, width: 208, height: 220, toJSON: () => ({}) };
      }
      return { x: 16, y: 598, top: 598, left: 16, right: 48, bottom: 630, width: 32, height: 32, toJSON: () => ({}) };
    });
    try {
      render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);
      fireEvent.click(screen.getByRole("button", { name: "Dune işlemleri" }));
      const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
      await waitFor(() => expect(Number.parseFloat(menu.style.top)).toBeLessThan(598));
      expect(Number.parseFloat(menu.style.top)).toBeGreaterThanOrEqual(8);
      expect(Number.parseFloat(menu.style.top) + 220).toBeLessThanOrEqual(598 - 4);
    } finally {
      rect.mockRestore();
      naturalHeight.mockRestore();
      Object.defineProperty(window, "innerHeight", { configurable: true, value: originalHeight });
    }
  });

  it("constrains an oversized menu to the viewport gutter", async () => {
    const originalHeight = window.innerHeight;
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 640 });
    const naturalHeight = vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.getAttribute("role") === "menu" ? 800 : 0;
    });
    const rect = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.getAttribute("role") === "menu") {
        return { x: 0, y: 0, top: 0, left: 0, right: 208, bottom: 800, width: 208, height: 800, toJSON: () => ({}) };
      }
      return { x: 16, y: 200, top: 200, left: 16, right: 48, bottom: 232, width: 32, height: 32, toJSON: () => ({}) };
    });
    try {
      render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);
      fireEvent.click(screen.getByRole("button", { name: "Dune işlemleri" }));
      const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
      await waitFor(() => expect(menu.style.maxHeight).toBe("624px"));
      expect(menu.style.top).toBe("8px");
      expect(menu.style.overflowY).toBe("auto");
    } finally {
      rect.mockRestore();
      naturalHeight.mockRestore();
      Object.defineProperty(window, "innerHeight", { configurable: true, value: originalHeight });
    }
  });

  it("keeps an oversized menu constrained after a viewport resize", async () => {
    const originalHeight = window.innerHeight;
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 640 });
    const naturalHeight = vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.getAttribute("role") === "menu" ? 800 : 0;
    });
    const rect = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.getAttribute("role") === "menu") {
        const height = Number.parseFloat(this.style.maxHeight) || 800;
        return { x: 0, y: 0, top: 0, left: 0, right: 208, bottom: height, width: 208, height, toJSON: () => ({}) };
      }
      return { x: 16, y: 200, top: 200, left: 16, right: 48, bottom: 232, width: 32, height: 32, toJSON: () => ({}) };
    });
    try {
      render(<MediaActionsMenu item={item} onTrash={vi.fn()} disabled={false} />);
      fireEvent.click(screen.getByRole("button", { name: "Dune işlemleri" }));
      const menu = screen.getByRole("menu", { name: "Dune işlemleri menüsü" });
      await waitFor(() => expect(menu.style.maxHeight).toBe("624px"));

      Object.defineProperty(window, "innerHeight", { configurable: true, value: 900 });
      fireEvent(window, new Event("resize"));
      await waitFor(() => expect(menu.style.maxHeight).toBe("884px"));
      expect(menu.style.top).toBe("8px");
      expect(menu.style.overflowY).toBe("auto");
    } finally {
      rect.mockRestore();
      naturalHeight.mockRestore();
      Object.defineProperty(window, "innerHeight", { configurable: true, value: originalHeight });
    }
  });
});
