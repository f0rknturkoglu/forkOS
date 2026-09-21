/**
 * Obsidian Vault köprüsü (istemci tarafı).
 *
 * Bilgi artık forkOS'un değil: yeni notlar doğrudan f0rknbrain Vault'unda
 * yaşar. Bu modül o köprünün TEK istemci yüzeyidir; hiçbir özellik modülü
 * kendi dosya yolu/URI mantığını kurmaz.
 *
 * Kurallar:
 *  - Dosya yolu ve Obsidian URI'leri SUNUCUDAN gelir (bkz. backend
 *    `app/integrations/obsidian`). İstemci yol birleştirmez.
 *  - Vault yazması DB durumunu değiştirmez; bu yüzden yalnız `vault-*`
 *    sorguları tazelenir.
 */
import { api, qs } from "@/core/api";

/**
 * `GET /obsidian/status` yanıtı. Uçların sözleşmesi burada ve `VaultItem` ile
 * birlikte tanımlıdır; Ayarlar ve Bilgi Kasası yüzeyleri bu tipi adıyla
 * kullandığı için dışa açıktır.
 */
export interface VaultStatus {
  configured: boolean;
  available: boolean;
  writable: boolean;
  readable: boolean;
  vault_name: string;
  managed_files: number;
  conflicts: number;
  conflict_details: Record<string, string[]>;
  invalid_files?: string[];
  diagnostic: string | null;
  /** Obsidian bağlantıları: kasayı aç / Inbox'ı göster / bugünün notu. */
  open_uri: string | null;
  inbox_uri: string | null;
  daily_uri: string | null;
}

/**
 * Vault durumunun TEK sözlüğü. "Kullanılamıyor" tek bir mesaja sıkıştırılmaz:
 * yapılandırılmamış / erişilemiyor / salt okunur / okunamadı ayrı ayrı
 * söylenir, çünkü her birinin kullanıcıya verdiği eylem farklıdır.
 */
export type VaultStateKind = "ready" | "read_only" | "not_configured" | "unavailable" | "unreadable";

/** Ekranda gösterilecek karşılık: kısa etiket (chip) + tek cümlelik yönlendirme. */
export interface VaultState {
  kind: VaultStateKind;
  chip: string;
  hint: string | null;
}

/**
 * Durum yanıtını kullanıcı diline çevirir. Öncelik sırası (yukarıdan aşağıya
 * ilk uyan kazanır): okuma hatası → yanıt yok → yapılandırılmamış →
 * erişilemiyor → salt okunur → sağlıklı.
 *
 * Bu fonksiyon Bilgi Kasası ve Ayarlar yüzeylerinin ortak kararıdır; iki yerde
 * ayrı ayrı yazılırsa aynı Vault iki farklı cümle söyler.
 */
export function describeVaultState(
  status: Pick<VaultStatus, "configured" | "available" | "writable" | "readable" | "diagnostic"> | undefined,
  isError: boolean,
): VaultState {
  if (isError) {
    return {
      kind: "unreadable",
      chip: "Vault durumu okunamadı",
      hint: "Yerel forkOS sunucusuna ulaşılamıyor olabilir; servisleri kontrol et.",
    };
  }
  if (!status) {
    return { kind: "unreadable", chip: "Vault durumu okunamadı", hint: null };
  }
  if (!status.configured) {
    return {
      kind: "not_configured",
      chip: "Vault yapılandırılmamış",
      hint:
        "forkOS'u Obsidian Vault runtime'ı ile başlat: `.env` içine OBSIDIAN_VAULT_HOST_PATH yaz, sonra " +
        "`make up-obsidian`. Vault olmadan bilgi köprüsü (notlar, günlükler) kapalı kalır.",
    };
  }
  if (!status.available) {
    return {
      kind: "unavailable",
      chip: "Vault erişilemiyor",
      hint: status.diagnostic ?? "Vault yolu erişilemiyor: bind mount yolunu ve dizin izinlerini kontrol et.",
    };
  }
  if (status.writable === false) {
    return {
      kind: "read_only",
      chip: "Vault bağlı · salt okunur",
      hint: "Vault bağlı ama yazılamıyor: okuma çalışır, yakalama ve günlük not yazma kapalı.",
    };
  }
  return { kind: "ready", chip: "Vault bağlı ✓", hint: null };
}

export interface VaultItem {
  forkos_id: string;
  forkos_type: string;
  title: string;
  /** Vault köküne GÖRELİ yol; tam sistem yolu asla dönmez. */
  relative_path: string;
  open_uri: string;
  mtime: number;
  size: number;
  note_kind: string | null;
  entity_type: string | null;
  project_id: string | null;
  journal_day: string | null;
  source_bookmark_id: string | null;
  relation_count: number;
}

/** Sorgu anahtarları: Vault yazması yalnız bunları tazeler. */
export const VAULT_STATUS_KEY = "vault-status";
export const VAULT_ITEM_KEY = "vault-item";

export const getVaultStatus = () => api.get<VaultStatus>("/obsidian/status");

export const refreshVaultIndex = () => api.post<VaultStatus>("/obsidian/index/refresh", {});

export const getVaultItem = (id: string) => api.get<VaultItem>(`/obsidian/items/${id}`);

/**
 * Kanonik bilgi notunu çözer, yoksa oluşturur. Kimlik forkOS kaydının
 * UUID'sidir; aynı çağrı ikinci kez yeni dosya üretmez.
 */
export const ensureVaultItem = (forkosId: string) => api.post<VaultItem>("/obsidian/ensure", { forkos_id: forkosId });

/** Hızlı yakalama: `00 Inbox/` altında yeni bilgi notu (kimliği sunucu üretir). */
export const captureVaultNote = (body: { body: string; relate_to?: string; tags?: string[] }) =>
  api.post<VaultItem>("/obsidian/capture", body);

/** Vault içi arama URI'si; parametre kodlaması sunucuda yapılır. */
export const getVaultSearchUri = (query: string) => api.get<{ uri: string }>(`/obsidian/uri/search${qs({ q: query })}`);

/**
 * Obsidian URI'sini işletim sistemine devreder.
 *
 * Obsidian kurulu değilse tarayıcı isteği yok sayar; forkOS çökmez ve
 * sayfa terk edilmez. URI sunucudan geldiği için istemci metni birleştirmez.
 */
export function openObsidianUri(uri: string): void {
  try {
    const anchor = document.createElement("a");
    anchor.href = uri;
    anchor.rel = "noopener";
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } catch {
    // Sessizce yut: harici uygulama açılamaması uygulamayı durdurmamalı.
  }
}
