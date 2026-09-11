/**
 * Her yerden yer imi kaydetme (Faz 4 — kullanıcının açık isteği).
 *
 * {url, title, collection?, entity_id?} tek aksiyon:
 *   1) POST /api/capture (idempotent, client_uuid ile)
 *   2) entity_id verilirse POST /api/links (from=bookmark, to=entity, "saved_from")
 * Toast NEREYE gittiğini yazar ve "Aç" ile yer iminde açar.
 */
import { useMutation } from "@tanstack/react-query";
import { api } from "./api";
import { invalidateAfter } from "./invalidation";
import { COLLECTION_LABELS } from "./types";
import { useToast } from "./ui";
import { useOnline } from "@/lib/hooks";
import { navigate } from "@/app/router";

interface SaveInput {
  url: string;
  title: string;
  collection?: "inbox" | "read_later" | "learning" | "reference" | "projects" | "archive";
  source?: string;
  entity_id?: string;
  /** Secili metin (alinti): bookmark.selection alanina yazilir. */
  selection?: string;
  /** Alintinin baglami: "s. 45", "01:23:45" gibi serbest metin. */
  note?: string;
  /** entity_id ile kurulacak bagin turu; alintilarda "highlights". */
  relation?: "saved_from" | "highlights";
}

export function useSaveToLibrary() {
  const toast = useToast();
  const online = useOnline();

  const mutation = useMutation({
    mutationFn: async ({
      url,
      title,
      collection = "inbox",
      source = "manual",
      entity_id,
      selection,
      note,
      relation = "saved_from",
    }: SaveInput) => {
      const result = await api.post<{ id: string; duplicate: boolean; collection: string }>("/capture", {
        url,
        title,
        collection,
        source,
        client_uuid: crypto.randomUUID(),
        ...(selection ? { selection } : {}),
        ...(note ? { note } : {}),
      });
      if (entity_id) {
        // Baginti istege bagli: capture basarili olmali, link hata yutulmaz.
        await api.post("/links", { from_id: result.id, to_id: entity_id, relation });
      }
      return result;
    },
    onSuccess: (result, input) => {
      invalidateAfter("bookmark.write");
      if (input.entity_id) invalidateAfter("link.write");
      const label = COLLECTION_LABELS[result.collection as keyof typeof COLLECTION_LABELS] ?? "kütüphaneye";
      toast.push(input.selection ? `Alıntı ${label} kaydedildi` : `"${input.title.slice(0, 40)}" ${label} eklendi`, {
        tone: result.duplicate ? "neutral" : "ok",
        action: {
          label: "Aç",
          run: () => {
            navigate(`/bookmarks?focus=${result.id}`);
          },
        },
      });
    },
  });

  return { save: mutation.mutateAsync, online };
}
