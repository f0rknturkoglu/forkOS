import { invalidateAfter } from "@/core/invalidation";
import { api } from "@/core/api";
import { createTask, invalidateTaskWrite } from "@/core/tasks";
import { readStored, writeStored } from "@/core/storage";

/**
 * Evrensel yakalama sozlesmesi (Faz 22).
 *
 * Uc tur tek intent katmanindan gecer: gorev (Faz 17 createTask), not
 * (Faz 21 /notes), baglanti (mevcut /capture). Bilesenler dogrudan farkli
 * body'ler uretmez. "Bugune al" tercihi task icinde yine uygulanir.
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
  pinned?: boolean;
  /** Doluysa not bu entity'ye notes_about ile baglanir. */
  relate_to?: string;
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
  id: string;
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
    // Tek istek: not + notes_about bagi backend'de ayni transaction'da (Faz 29).
    const note = await api.post<{ id: string }>("/notes", {
      body: intent.text,
      pinned: intent.note?.pinned ?? false,
      ...(intent.note?.relate_to ? { relate_to: intent.note.relate_to } : {}),
    });
    invalidateAfter("note.write", "link.write");
    return { kind: "note", id: note.id };
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
