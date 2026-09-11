import { api } from "./api";
import { invalidateAfter } from "./invalidation";

/**
 * Iki entity arasinda iliski kurar (kural 14 icin tek yazma noktasi).
 *
 * Neden ayri yardimci: yuzeyler (detay sayfalari) kendi `post("/links")`
 * cagrilarini yazinca her biri kendi tazeleme listesini kuruyordu; ortak yol
 * iliski sonrasi `related`/`backlinks`/`graph` tazelemesini garanti eder.
 * `RelatedPanel` de ayni sozlesmeyi kullanir.
 */
export async function linkEntities(fromId: string, toId: string, relation = "related"): Promise<void> {
  await api.post("/links", { from_id: fromId, to_id: toId, relation });
  invalidateAfter("link.write");
}
