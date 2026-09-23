/**
 * Bilgi Kasası — forkOS'un Obsidian Vault köprüsü.
 *
 * Bu sayfa bir not uygulaması DEGILDIR: not listesi, markdown editörü, tuval,
 * ek, klasör ve graf bilinçli olarak yoktur. Bilgi f0rknbrain Vault'unda yaşar;
 * forkOS burada yalnız kasaya giden yolları, indeks durumunu ve eski
 * `/notes?focus=<uuid>` derin bağlantılarının çözümünü gösterir.
 *
 * Odak (`?focus=`) sözleşmesi: Vault'taki karşılığı çözülür ve Obsidian'a
 * devredilir; not içeriği forkOS içinde YENİDEN ÇİZİLMEZ. Çözülemezse kayıt
 * ya taşınmamış ya da yeniden adlandırılmıştır — eski veritabanı notlarına
 * düşmek yasaktır (Faz 3).
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  CalendarDays,
  ExternalLink,
  FileWarning,
  Inbox,
  RefreshCw,
  Search,
} from "lucide-react";
import { useHashRoute } from "@/app/router";
import { invalidateAfter } from "@/core/invalidation";
import {
  describeVaultState,
  getVaultItem,
  getVaultSearchUri,
  getVaultStatus,
  openObsidianUri,
  refreshVaultIndex,
  VAULT_ITEM_KEY,
  VAULT_STATUS_KEY,
} from "@/core/obsidian";
import { Button, Chip, Input, PageFrame, Section, Spinner, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";

/** Cakisma/gecersiz kayit uyarilarinda gosterilen en fazla satir. */
const WARNING_ROWS = 3;

export function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const route = useHashRoute();
  const focus = route.params.get("focus") ?? "";
  const online = useOnline();
  const toast = useToast();

  const statusQuery = useQuery({
    queryKey: [VAULT_STATUS_KEY],
    queryFn: getVaultStatus,
  });
  const status = statusQuery.data;
  // Vault durumu TEK bir "kullanılamıyor" mesajına sıkıştırılmaz (§28);
  // sözlük ve öncelik sırası `@/core/obsidian` içinde ortaktır.
  const vaultState = describeVaultState(status, statusQuery.isError);
  const vaultReady = vaultState.kind === "ready" || vaultState.kind === "read_only";
  const invalidFiles = status?.invalid_files ?? [];
  const conflicts = Object.entries(status?.conflict_details ?? {});

  const refresh = useMutation({
    mutationFn: refreshVaultIndex,
    onSuccess: () => {
      // Vault yazmasi DB durumunu degistirmez: yalniz vault-* sorgulari tazelenir.
      invalidateAfter("obsidian.write");
      toast.push("Vault indeksi yenilendi.", { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`İndeks yenilenemedi: ${error.message}`, { tone: "danger" }),
  });

  const search = useMutation({
    mutationFn: (query: string) => getVaultSearchUri(query),
    onSuccess: ({ uri }) => openObsidianUri(uri),
    onError: (error: Error) => toast.push(`Arama açılamadı: ${error.message}`, { tone: "danger" }),
  });

  // Eski kayit defteri derin baglantisi: icerik burada cizilmez, yalniz cozulur.
  const itemQuery = useQuery({
    queryKey: [VAULT_ITEM_KEY, focus],
    queryFn: () => getVaultItem(focus),
    enabled: Boolean(focus),
    retry: false,
  });

  const openActions = [
    { id: "vault", label: "Obsidian'ı Aç", icon: ExternalLink, uri: status?.open_uri },
    { id: "inbox", label: "Inbox", icon: Inbox, uri: status?.inbox_uri },
    { id: "daily", label: "Bugünün Notu", icon: CalendarDays, uri: status?.daily_uri },
  ];

  const focusItem = itemQuery.data;

  return (
    <PageFrame className="p-4 sm:p-6">
      <div className="mx-auto max-w-3xl space-y-4">
        <header className="flex items-start gap-3">
          <BookOpen size={22} className="mt-0.5 shrink-0 text-icon" />
          <div className="min-w-0">
            <h1 className="text-title text-primary">
              {status?.vault_name ? `Bilgi Kasası — ${status.vault_name}` : "Bilgi Kasası"}
            </h1>
            <p className="mt-1 text-body text-secondary">
              forkOS operasyonel verileri yönetir; notlar ve uzun süreli bilgi f0rknbrain Obsidian Vault&apos;ta yaşar.
            </p>
          </div>
        </header>

        <Section title="Kasa">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              {openActions.map(({ id, label, icon: Icon, uri }) => (
                <Button key={id} disabled={!uri} onClick={() => uri && openObsidianUri(uri)}>
                  <Icon size={13} /> {label}
                </Button>
              ))}
              <div className="flex items-center gap-2">
                <Input
                  value={searchQuery}
                  onChange={setSearchQuery}
                  placeholder="Vault'ta ara"
                  ariaLabel="Vault arama sorgusu"
                  disabled={!vaultReady}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && searchQuery.trim()) search.mutate(searchQuery.trim());
                  }}
                />
                <Button
                  disabled={!vaultReady || !searchQuery.trim() || search.isPending}
                  onClick={() => search.mutate(searchQuery.trim())}
                >
                  <Search size={13} /> Vault&apos;ta Ara
                </Button>
              </div>
            </div>

            {statusQuery.isLoading ? (
              <Spinner label="Vault durumu yükleniyor…" />
            ) : (
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-meta text-secondary">
                  <span>{status?.managed_files ?? 0} yönetilen not</span>
                  {vaultState.kind === "ready" && <Chip tone="ok">{vaultState.chip}</Chip>}
                  {vaultState.kind === "read_only" && <Chip tone="warn">{vaultState.chip}</Chip>}
                  {(vaultState.kind === "not_configured" || vaultState.kind === "unavailable") && (
                    <Chip tone="danger">{vaultState.chip}</Chip>
                  )}
                  {vaultState.kind === "unreadable" && <Chip tone="danger">{vaultState.chip}</Chip>}
                  <span className="flex-1" />
                  <Button
                    variant="ghost"
                    disabled={!online || !vaultReady || refresh.isPending}
                    onClick={() => refresh.mutate()}
                  >
                    <RefreshCw size={13} /> İndeksi yenile
                  </Button>
                </div>

                {vaultState.hint ? (
                  <p className={cx("text-meta", vaultState.kind === "read_only" ? "text-warn" : "text-danger")}>
                    {vaultState.hint}
                  </p>
                ) : null}

                {conflicts.length > 0 ? (
                  <div className="rounded-control border border-warn-border bg-warn-surface p-2.5">
                    <p className="flex items-center gap-1.5 text-meta font-medium text-warn">
                      <AlertTriangle size={13} /> {status?.conflicts ?? conflicts.length} çakışma: aynı forkOS kimliği
                      birden fazla dosyada
                    </p>
                    <ul className="mt-1 space-y-0.5">
                      {conflicts.slice(0, WARNING_ROWS).map(([id, paths]) => (
                        <li key={id} className="font-mono text-micro text-warn">
                          {id.slice(0, 8)}… → {paths.join(", ")}
                        </li>
                      ))}
                    </ul>
                    {conflicts.length > WARNING_ROWS ? (
                      <p className="mt-1 text-micro text-warn">+{conflicts.length - WARNING_ROWS} kayıt daha</p>
                    ) : null}
                  </div>
                ) : null}

                {invalidFiles.length > 0 ? (
                  <div className="rounded-control border border-warn-border bg-warn-surface p-2.5">
                    <p className="flex items-center gap-1.5 text-meta font-medium text-warn">
                      <FileWarning size={13} /> {invalidFiles.length} dosyada geçersiz üst veri var
                    </p>
                    <ul className="mt-1 space-y-0.5">
                      {invalidFiles.slice(0, WARNING_ROWS).map((file) => (
                        <li key={file} className="font-mono text-micro text-warn">
                          {file}
                        </li>
                      ))}
                    </ul>
                    {invalidFiles.length > WARNING_ROWS ? (
                      <p className="mt-1 text-micro text-warn">+{invalidFiles.length - WARNING_ROWS} dosya daha</p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </Section>

        {focus ? (
          <Section title="Bağlantıdan gelen kayıt">
            {itemQuery.isLoading ? (
              <Spinner label="Vault kaydı çözülüyor…" />
            ) : focusItem ? (
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Chip tone="ok">Taşınmış not</Chip>
                  <span className="min-w-0 flex-1 truncate text-heading text-primary">{focusItem.title}</span>
                </div>
                <p className="truncate font-mono text-meta text-secondary">{focusItem.relative_path}</p>
                <Button onClick={() => openObsidianUri(focusItem.open_uri)}>
                  <ExternalLink size={13} /> Obsidian&apos;da Aç
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-heading text-warn">Vault&apos;ta açılamadı</p>
                <p className="text-meta text-secondary">
                  Bu kayıt Vault&apos;a taşınmamış ya da yeniden adlandırılmış olabilir. forkOS eski not arşivini artık
                  okumaz; kaydın Obsidian&apos;daki karşılığını Vault aramasında bulabilirsin.
                </p>
                <p className="truncate font-mono text-micro text-muted">{focus}</p>
              </div>
            )}
          </Section>
        ) : null}
      </div>
    </PageFrame>
  );
}
