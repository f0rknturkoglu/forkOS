/**
 * Kart yazimlarindan sonra tazeleme (kural 14): "flashcard.write" haritada
 * tanimli -- Today, Istatistik, Etkinlik ve Degerlendirme panelleri de bu
 * olayla tazelenir (bkz. core/invalidation.ts).
 */
import { invalidateAfter } from "@/core/invalidation";

export function refreshFlashcards(): void {
  invalidateAfter("flashcard.write");
}
