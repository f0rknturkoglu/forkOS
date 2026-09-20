import { invalidateAfter } from "@/core/invalidation";
import { api } from "@/core/api";
import { captureVaultNote, type VaultItem } from "@/core/obsidian";
import { createTask, invalidateTaskWrite } from "@/core/tasks";
import { readStored, writeStored } from "@/core/storage";

/**
 * Evrensel yakalama sozlesmesi (Faz 22).
 *
 * Uc tur tek intent katmanindan gecer: gorev (Faz 17 createTask), not
 * (Obsidian Vault `/obsidian/capture`), baglanti (mevcut /capture). Bilesenler
 * dogrudan farkli body'ler uretmez. "Bugune al" tercihi task icinde yine
 * uygulanir.
 *
 * Not turu artik forkOS veritabanina YAZMAZ: bilgi notu Vault'ta yasar, bu
 * yuzden yalniz Vault sorgulari tazelenir.
 */

export type CaptureKind = "task" | "note" | "link" | "flashcard";

const CAPTURE_KIND_KEY = "captureKind";

export function readCaptureKindPreference(): CaptureKind {
  const value = readStored(CAPTURE_KIND_KEY);
  return value === "note" || value === "link" || value === "flashcard" ? value : "task";
}

export function writeCaptureKindPreference(kind: CaptureKind): void {
  if (typeof localStorage === "undefined") return;
  writeStored(CAPTURE_KIND_KEY, kind);
}

interface TaskCaptureOptions {
  priority?: number;
  due_at?: string;
  /** Açıkça verilirse tercihten önce gelir; yoksa "bugüne al" tercihi. */
  plan_day?: string;
  recur?: string;
  project_id?: string;
  tags?: string[];
}

interface NoteCaptureOptions {
  /** Doluysa not Vault frontmatter'inda bu entity'ye baglanir. */
  relate_to?: string;
  /** Vault dosya adini/basligini belirler; yoksa govdeden turetilir. */
  title?: string;
}

interface FlashcardCaptureOptions {
  deck_id: string;
  /** On yuz (soru). */
  front: string;
  /** Arka yuz (cevap). */
  back: string;
}

interface LinkCaptureOptions {
  collection?: "inbox" | "reference" | "learning";
  tags?: string[];
}

interface CaptureIntent {
  kind: CaptureKind;
  /** Task basligi / not govdesi / baglanti basligi. */
  text: string;
  url?: string;
  task?: TaskCaptureOptions;
  note?: NoteCaptureOptions;
  link?: LinkCaptureOptions;
  flashcard?: FlashcardCaptureOptions;
}

interface CaptureResult {
  kind: CaptureKind;
  /** Okunan kaydin kimligi; not turunde Vault dosyasinin `forkos_id`'sidir. */
  id: string;
  /** Yalniz not turunde dolar: Vault kaydi (`open_uri`, `relative_path`). */
  vault?: VaultItem;
}

/** Intent'i dogru domain servisine yonlendirir; invalidation ture ozeldir. */
export async function capture(intent: CaptureIntent): Promise<CaptureResult> {
  if (intent.kind === "task") {
    const todo = await createTask({
      title: intent.text,
      priority: intent.task?.priority,
      due_at: intent.task?.due_at,
      plan_day: intent.task?.plan_day,
      recur: intent.task?.recur,
      project_id: intent.task?.project_id,
      tags: intent.task?.tags,
    });
    invalidateTaskWrite();
    return { kind: "task", id: todo.id };
  }

  if (intent.kind === "flashcard") {
    const payload = intent.flashcard;
    if (!payload) throw new Error("Deste secilmedi");
    const card = await api.post<{ id: string }>(`/flashcard/decks/${payload.deck_id}/cards`, {
      front: payload.front,
      back: payload.back,
    });
    invalidateAfter("flashcard.write");
    return { kind: "flashcard", id: card.id };
  }

  if (intent.kind === "note") {
    // Bilgi notu forkOS'ta DEGIL Vault'ta yasar: DB'de not kaydi acilmaz ve
    // forkOS'a ozel alanlar (`pinned`) gonderilmez. Vault basligini govdeden
    // turettigi icin verilen baslik govdenin ilk satiri olur.
    const title = intent.note?.title?.trim();
    const item = await captureVaultNote({
      body: title ? `${title}\n\n${intent.text}` : intent.text,
      ...(intent.note?.relate_to ? { relate_to: intent.note.relate_to } : {}),
    });
    invalidateAfter("obsidian.write");
    return { kind: "note", id: item.forkos_id, vault: item };
  }

  const result = await api.post<{ id: string }>("/capture", {
    url: intent.url ?? intent.text,
    title: intent.url ? intent.text : "",
    collection: intent.link?.collection ?? "inbox",
    source: "capture",
    tags: intent.link?.tags ?? [],
  });
  invalidateAfter("bookmark.write");
  return { kind: "link", id: result.id };
}
