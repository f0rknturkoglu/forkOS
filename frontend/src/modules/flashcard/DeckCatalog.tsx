import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Search, Download } from "lucide-react";
import { api, qs } from "@/core/api";
import { Button, Chip, Empty, Field, Input, Modal, Section, SkeletonRows, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";
import { refreshFlashcards } from "./invalidate";
import type { ImportResult } from "./types";

type S = components["schemas"];

export function DeckCatalog({ onOpen }: { onOpen: (id: string) => void }) {
  const online = useOnline();
  const toast = useToast();
  const [draft, setDraft] = useState("english");
  const [search, setSearch] = useState("english");
  const [selected, setSelected] = useState<number | null>(null);
  const catalog = useQuery({
    queryKey: ["flashcard", "catalog", search],
    queryFn: () => api.get<S["SharedDeckOut"][]>(`/flashcard/catalog${qs({ search })}`),
    enabled: online,
    staleTime: 300_000,
    retry: false,
  });
  const preview = useQuery({
    queryKey: ["flashcard", "catalog-preview", selected],
    queryFn: () => api.get<S["SharedDeckPreview"]>(`/flashcard/catalog/${selected}`),
    enabled: selected !== null && online,
    retry: false,
  });
  const download = useMutation({
    mutationFn: (id: number) => api.post<ImportResult>(`/flashcard/catalog/${id}/import`, {}),
    onSuccess: (result) => {
      refreshFlashcards();
      setSelected(null);
      onOpen(result.deck_id);
      toast.push(`${result.added} kart eklendi.`, { tone: "ok" });
    },
    onError: (error: Error) => toast.push(error.message, { tone: "danger" }),
  });
  return (
    <Section
      title="Deste keşfet"
      hint={
        <a
          href="https://ankiweb.net/shared/decks"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-accent"
        >
          AnkiWeb <ExternalLink size={12} />
        </a>
      }
    >
      <form
        className="mb-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          const link = /^https:\/\/(?:www\.)?ankiweb\.net\/shared\/info\/(\d+)\/?$/.exec(draft.trim());
          if (link && Number(link[1]) > 0 && Number(link[1]) <= 4294967295) setSelected(Number(link[1]));
          else setSearch(draft.trim() || "english");
        }}
      >
        <Input
          ariaLabel="Deste kataloğunda ara"
          placeholder="Deste ara veya AnkiWeb bağlantısını yapıştır…"
          value={draft}
          onChange={setDraft}
          className="min-w-0 flex-1"
        />
        <Button type="submit" disabled={!online}>
          <Search size={14} /> {draft.trim().startsWith("https://ankiweb.net/shared/info/") ? "İncele" : "Ara"}
        </Button>
      </form>
      {catalog.isPending && online ? (
        <SkeletonRows rows={3} />
      ) : catalog.isError ? (
        <Empty title="Katalog alınamadı">
          <span className="mb-2 block text-meta text-secondary">{(catalog.error as Error).message}</span>
          <Button onClick={() => void catalog.refetch()}>Yeniden dene</Button>
        </Empty>
      ) : !online && !catalog.data ? (
        <Empty>Kataloğu açmak için internete bağlan.</Empty>
      ) : !catalog.data?.length ? (
        <Empty>Bu aramada deste bulunamadı.</Empty>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {catalog.data.map((deck) => (
            <article key={deck.id} className="flex min-w-0 flex-col rounded-card border border-subtle p-3 stack-y-2">
              <h3 className="break-words text-body font-medium">{deck.title}</h3>
              <div className="flex flex-wrap gap-2">
                <Chip>{deck.notes} not</Chip>
                {deck.has_media && <Chip variant="outline">Medya içerir</Chip>}
              </div>
              <div className="mt-auto flex items-center justify-between gap-2 pt-2">
                <a
                  href={deck.url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`${deck.title} — AnkiWeb’de aç`}
                  className="text-meta text-secondary hover:text-accent"
                >
                  <ExternalLink size={14} />
                </a>
                <Button size="sm" disabled={!online} onClick={() => setSelected(deck.id)}>
                  <Download size={13} /> İncele ve ekle
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
      <Modal
        open={selected !== null}
        onClose={() => {
          if (!download.isPending) setSelected(null);
        }}
        title={preview.data?.title ?? "Deste önizlemesi"}
      >
        {preview.isPending ? (
          <SkeletonRows rows={3} />
        ) : preview.isError ? (
          <Empty>
            <span className="mb-2 block">{(preview.error as Error).message}</span>
            <Button disabled={!online} onClick={() => void preview.refetch()}>
              Yeniden dene
            </Button>
          </Empty>
        ) : (
          preview.data && (
            <div className="stack-y-3">
              <p className="text-meta text-secondary">
                {preview.data.notes} not · {(preview.data.size_bytes / 1_000_000).toFixed(1)} MB
              </p>
              {preview.data.samples.map((sample, index) => (
                <div key={index} className="rounded-control bg-surface-sunken p-3 text-meta stack-y-1">
                  {sample.map((field, i) => (
                    <p key={i} className="break-words">
                      {field}
                    </p>
                  ))}
                </div>
              ))}
              {preview.data.has_media && (
                <p className="text-meta text-warn">Yalnız metin kartları aktarılır; ses ve görseller eklenmez.</p>
              )}
              <Field label="Kaynak">
                <a href={preview.data.url} target="_blank" rel="noreferrer" className="text-meta text-accent">
                  AnkiWeb’de incele <ExternalLink size={12} className="inline" />
                </a>
              </Field>
              <Button
                variant="primary"
                disabled={!online || download.isPending}
                onClick={() => download.mutate(selected!)}
              >
                <Download size={14} />
                {download.isPending ? "İndiriliyor…" : "Kartlara ekle"}
              </Button>
            </div>
          )
        )}
      </Modal>
    </Section>
  );
}
