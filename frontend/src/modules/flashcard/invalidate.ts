/**
 * invalidateAfter haritasi (kural 14) geregi mutation sonrasi anlamli olay
 * bildirilir: "flashcard.write". Ana agent entegrasyonda AFTER'a bu anahtar
 * eklenecek; o zamana kadar tipi zorlamak icin cast gerekli.
 */
import { invalidateAfter } from "@/core/invalidation";

export function refreshFlashcards(): void {
  invalidateAfter("flashcard.write" as never);
}
