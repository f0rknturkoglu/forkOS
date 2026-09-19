/**
 * Medya modulunun paylasilan sorgu anahtarlari.
 *
 * Ayni ucu iki farkli anahtarla sormak TanStack'in dedupe'unu devre disi
 * birakir: uç iki kez cekilir ve iki onbellek olusur. Koleksiyon listesi tam
 * da boyleydi (["media-collections"] vs ["media","collections"]); anahtar
 * artik tek yerde.
 */
export const MEDIA_COLLECTIONS_QUERY_KEY = ["media", "collections"] as const;
