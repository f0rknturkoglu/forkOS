import { MutationCache, QueryClient } from "@tanstack/react-query";
import { emitGlobalToast } from "./ui";

type MutationLike = { meta?: Record<string, unknown> };

export function mutationErrorHandler(
  _error: unknown,
  _variables: unknown,
  _context: unknown,
  mutation: MutationLike,
): void {
  if (mutation.meta?.silentError) return;
  emitGlobalToast({
    message: "İşlem tamamlanamadı. Bağlantıyı kontrol edip tekrar deneyebilirsin.",
    options: { tone: "danger" },
  });
}

/**
 * Tek QueryClient. main.tsx bunu Provider'a verir.
 *
 * Burada durmasinin sebebi: komut paletinin komutlari React agacinin
 * DISINDA calisir (registerModule icindeki run()), yani useQueryClient
 * cagiramazlar. Yazma yapan bir komut bitince invalidate() ile ekrani
 * tazeler -- location.reload() yerine.
 */
export const queryClient = new QueryClient({
  mutationCache: new MutationCache({ onError: mutationErrorHandler }),
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

/** Yazma sonrasi tazeleme. useInvalidate ile ayni anahtarlari alir. */
export function invalidate(...keys: string[]): void {
  for (const key of keys) queryClient.invalidateQueries({ queryKey: [key] });
}
