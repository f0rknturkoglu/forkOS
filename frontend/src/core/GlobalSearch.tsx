import { useQuery } from "@tanstack/react-query";
import { api, qs } from "./api";
import { useDebounced } from "@/lib/hooks";
import type { Entity } from "./types";
import { entityRoute as routeFor } from "./entityRegistry";

/** Tip -> rota kayit defterinden gelir (kural 13); burada sabit YOK. */
export function entityRoute(entity: Entity): string {
  return "#" + routeFor(entity.type, entity.id);
}

/** Command Palette icinde kullanilan global arama. Bos sorguda ag'a cikmaz. */
export function useGlobalSearch(query: string) {
  const debounced = useDebounced(query.trim(), 200);
  return useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.get<Record<string, Entity[]>>(`/search${qs({ q: debounced, limit: 30, grouped: true })}`),
    enabled: debounced.length >= 2,
    staleTime: 10_000,
  });
}


