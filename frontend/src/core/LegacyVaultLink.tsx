import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { navigate, useHashRoute } from "@/app/router";
import { getVaultItem, openObsidianUri, VAULT_ITEM_KEY } from "@/core/obsidian";
import { Button } from "@/core/ui";

/** Compatibility resolver only: knowledge remains owned by Obsidian. */
export function LegacyVaultLink() {
  const { params } = useHashRoute();
  const focus = params.get("focus") ?? "";
  const valid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(focus);
  const opened = useRef<string | null>(null);
  const query = useQuery({
    queryKey: [VAULT_ITEM_KEY, focus],
    queryFn: () => getVaultItem(focus),
    enabled: valid,
    retry: false,
  });
  useEffect(() => {
    if (!focus) navigate("/settings?tab=brain", { replace: true });
  }, [focus]);
  useEffect(() => {
    if (query.data && opened.current !== focus) {
      opened.current = focus;
      openObsidianUri(query.data.open_uri);
    }
  }, [query.data, focus]);
  const message = !valid
    ? "Not bağlantısındaki kimlik geçersiz."
    : query.isPending
      ? "Not Obsidian Vault içinde aranıyor…"
      : query.error
        ? `Not açılamadı. ${query.error.message}`
        : `“${query.data?.title}” Obsidian'a gönderildi.`;
  return (
    <div className="mx-auto max-w-2xl stack-y-4 p-8">
      <p className="text-title">Obsidian not bağlantısı</p>
      <p role={query.error || !valid ? "alert" : "status"} className="text-body text-secondary">
        {message}
      </p>
      <div className="flex flex-wrap gap-2">
        {query.data && <Button onClick={() => openObsidianUri(query.data!.open_uri)}>Obsidian'da aç</Button>}
        {query.error && <Button onClick={() => void query.refetch()}>Tekrar dene</Button>}
        <Button variant="ghost" onClick={() => navigate("/settings?tab=brain")}>
          Vault ayarları
        </Button>
      </div>
    </div>
  );
}
