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
 * cagiramazlar. Yazma yapan bir komut bitince invalidateAfter() ile ekrani
 * tazeler -- location.reload() yerine.
 *
 * Lazim olunca kurulur: testler @tanstack/react-query'i mock'ladiginda
 * modul yuklemesi patlamasin diye (queryClient.ts'e dokunan her dosya
 * test suiti tarafindan import edilebiliyor).
 */
let _queryClient: QueryClient | undefined;

export function queryClient(): QueryClient {
  if (!_queryClient) {
    _queryClient = new QueryClient({
      mutationCache: new MutationCache({ onError: mutationErrorHandler }),
      defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
    });
  }
  return _queryClient;
}
