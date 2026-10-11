// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ReviewView } from "./ReviewView";
import { invalidateAfter } from "@/core/invalidation";
const harness = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  navigate: vi.fn(),
  client: null as QueryClient | null,
}));
vi.mock("@/core/queryClient", () => ({ queryClient: () => harness.client! }));
vi.mock("@/core/api", () => ({ api: { get: harness.get, post: harness.post } }));
vi.mock("@/app/router", () => ({ navigate: harness.navigate }));
vi.mock("@/modules/pomodoro/dock", () => ({ openPomodoro: vi.fn() }));
let topics = 0,
  cards = 0;
const clients: QueryClient[] = [];
beforeEach(() => {
  topics = 0;
  cards = 0;
  harness.navigate.mockReset();
  harness.post.mockReset().mockImplementation(async () => {
    topics = 0;
    return {};
  });
  harness.get.mockReset().mockImplementation(async (path: string) =>
    path.includes("/flashcard/decks")
      ? [{ id: "deck", title: "Backend", due_count: cards, new_count: 0, card_count: cards }]
      : {
          due_today: Array.from({ length: topics }, (_, i) => ({
            id: `t${i}`,
            title: `Konu ${i}`,
            area_title: "Backend",
            next_review_at: new Date().toISOString(),
            mastery: 30,
          })),
          overdue: [],
          upcoming: [],
          new_topics: [],
          weak: [],
        },
  );
});
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((c) => c.clear());
});
function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  clients.push(client);
  harness.client = client;
  const open = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <ReviewView onOpenTopic={open} />
    </QueryClientProvider>,
  );
  return { client, open };
}
it.each([
  [0, 0],
  [3, 0],
  [0, 18],
  [3, 18],
])("independent daily queues: %i topics, %i cards", async (t, c) => {
  topics = t;
  cards = c;
  show();
  expect(await screen.findByText(`${c} kart bekliyor · 0 yeni kart`)).toBeTruthy();
  if (t) expect(await screen.findByText(`${t} konu · Tekrar zamanı bugün gelenler`)).toBeTruthy();
  else expect(await screen.findByText("Bugün tekrar edilecek konu yok")).toBeTruthy();
});
it("opens topic and existing deck review with return link", async () => {
  topics = 3;
  cards = 18;
  const { open } = show();
  fireEvent.click(await screen.findByText("Konu 0"));
  expect(open).toHaveBeenCalledWith("t0");
  fireEvent.click(screen.getByRole("button", { name: "Backend · 18 bekleyen" }));
  expect(harness.navigate).toHaveBeenCalledWith("/flashcard?deck=deck&review=due&return=learning-review");
});
it("topic completion refreshes topics; card mutation refreshes cards independently", async () => {
  topics = 1;
  cards = 18;
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Tekrar yap" }));
  fireEvent.click(screen.getByRole("button", { name: "Kolay" }));
  await waitFor(() => expect(screen.queryByText("Konu 0")).toBeNull());
  expect(screen.getByText("18 kart bekliyor · 0 yeni kart")).toBeTruthy();
  cards = 0;
  invalidateAfter("flashcard.write");
  await waitFor(() => expect(screen.getByText("0 kart bekliyor · 0 yeni kart")).toBeTruthy());
});
