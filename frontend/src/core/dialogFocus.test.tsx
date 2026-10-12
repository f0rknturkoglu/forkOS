// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it } from "vitest";
import { confirmDialog, DialogHost } from "./dialog";
import { Button, Input, Modal } from "./ui";

afterEach(cleanup);

function Nested() {
  const [outer, setOuter] = useState(false);
  const [inner, setInner] = useState(false);
  return (
    <>
      <Button onClick={() => setOuter(true)}>Aç</Button>
      <Modal open={outer} title="Dış pencere" onClose={() => setOuter(false)}>
        <Button onClick={() => setInner(true)}>İç pencereyi aç</Button>
        <Modal open={inner} title="İç pencere" onClose={() => setInner(false)}>
          <Input ariaLabel="İç alan" value="" onChange={() => {}} />
          <Button>İç son</Button>
        </Modal>
      </Modal>
    </>
  );
}

it("Escape only closes the top dialog and restores its opener", () => {
  render(<Nested />);
  screen.getByRole("button", { name: "Aç" }).focus();
  fireEvent.click(screen.getByRole("button", { name: "Aç" }));
  const opener = screen.getByRole("button", { name: "İç pencereyi aç" });
  opener.focus();
  fireEvent.click(opener);
  fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  expect(screen.queryByRole("dialog", { name: "İç pencere" })).toBeNull();
  expect(screen.getByRole("dialog", { name: "Dış pencere" })).toBeTruthy();
  expect(document.activeElement).toBe(opener);
});

it("Tab stays in the top dialog instead of moving into its parent", () => {
  render(<Nested />);
  fireEvent.click(screen.getByRole("button", { name: "Aç" }));
  fireEvent.click(screen.getByRole("button", { name: "İç pencereyi aç" }));
  screen.getByRole("button", { name: "İç son" }).focus();
  fireEvent.keyDown(document.activeElement!, { key: "Tab" });
  const inner = screen.getByRole("dialog", { name: "İç pencere" });
  expect(document.activeElement).toBe(within(inner).getByRole("button", { name: "Kapat" }));
});

it("focus trap ignores descendants of hidden sections", () => {
  render(
    <Modal open title="Gizli alanlar" onClose={() => {}}>
      <div hidden>
        <Input ariaLabel="Gizli" value="" onChange={() => {}} />
      </div>
      <Button>Son</Button>
    </Modal>,
  );
  screen.getByRole("button", { name: "Kapat" }).focus();
  fireEvent.keyDown(document.activeElement!, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Son" }));
});

it("confirmation traps focus and returns it on cancel", async () => {
  let result: Promise<boolean> | undefined;
  render(
    <>
      <Button
        onClick={() => {
          result = confirmDialog({ title: "Silme onayı", confirmLabel: "Sil" });
        }}
      >
        Silmek için aç
      </Button>
      <DialogHost />
    </>,
  );
  const opener = screen.getByRole("button", { name: "Silmek için aç" });
  opener.focus();
  fireEvent.click(opener);
  const dialog = screen.getByRole("alertdialog", { name: "Silme onayı" });
  within(dialog).getByRole("button", { name: "Sil" }).focus();
  fireEvent.keyDown(document.activeElement!, { key: "Tab" });
  expect(dialog.contains(document.activeElement)).toBe(true);
  fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  expect(await result).toBe(false);
  expect(document.activeElement).toBe(opener);
});

it("a second confirmation request is rejected without stranding the first", async () => {
  let first: Promise<boolean> | undefined;
  let second: Promise<boolean> | undefined;
  render(
    <>
      <Button
        onClick={() => {
          first = confirmDialog({ title: "İlk onay", confirmLabel: "Onayla" });
          second = confirmDialog({ title: "İkinci onay", confirmLabel: "Onayla" });
        }}
      >
        Çift istek
      </Button>
      <DialogHost />
    </>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Çift istek" }));
  expect(screen.getByRole("alertdialog", { name: "İlk onay" })).toBeTruthy();
  expect(await second).toBe(false);
  fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  expect(await first).toBe(false);
});
