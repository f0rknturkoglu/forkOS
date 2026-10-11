import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Circle, HelpCircle, X } from "lucide-react";
import { api } from "@/core/api";
import { getVaultStatus, VAULT_STATUS_KEY } from "@/core/obsidian";
import { PROACTIVITY_STATUS_KEY } from "@/core/proactivity";
import { Chip, Disclosure, Section, cx } from "@/core/ui";
import type { AppSettings } from "@/core/types";

/**
 * Kurulum kontrol listesi (§87).
 *
 * Karmaşık bir onboarding SİHİRBAZI değildir ve "her şey açık olmalı" DEMEZ.
 * İki ayrı katman vardır:
 *
 *   Çekirdek  — yerel çalışma alanı (API + veritabanı) ve bilgi kasası.
 *               Bunlardan biri eksikse liste görünür.
 *   İsteğe bağlı — GitHub, Google Calendar, kariyer profili, proaktivite.
 *               Bunların eksik olması "kurulum tamamlanmadı" DEĞİLDİR; bu
 *               yüzden listeyi açmazlar, yalnız katlanmış bir notta anılırlar.
 *
 * Bu yüzden kurulumu tamamlanmış kullanıcı (bu uygulamanın gerçek kullanıcısı)
 * yüzeyi hiç görmez; entegrasyon bağlamamış olmak da onu rahatsız etmez.
 *
 * Tüm durumlar mevcut uçlardan ve PAYLAŞILAN anahtarlardan okunur; yeni bir
 * "setup" ucu yoktur.
 */

const DISMISS_KEY = "forkos.setup.dismissed";

/** Bilinmiyor ≠ eksik: okunamayan bir adım "doğrulanamadı" der, "eksik" demez. */
type StepState = "ready" | "missing" | "unknown";

interface SetupStep {
  id: string;
  label: string;
  state: StepState;
  /** Eksik adımın gidilecek yeri. */
  href: string;
}

function dismissedInStorage(): boolean {
  // Statik render/test ortamında localStorage olmayabilir: varsayılan "kapatılmadı".
  try {
    return globalThis.localStorage?.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

export function SetupChecklist() {
  const [dismissed, setDismissed] = useState(dismissedInStorage);
  // Kabuğun da çektiği anahtar: yerel API'nin (ve dolayısıyla veritabanının)
  // ayakta olduğunun tek kanıtı gelen yanıttır.
  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
    retry: false,
  });
  const vault = useQuery({
    queryKey: [VAULT_STATUS_KEY],
    queryFn: getVaultStatus,
    retry: false,
  });
  /* Kariyer profili ayarlarda saklanır: kabuğun zaten çektiği anahtar. */
  const github = useQuery({
    queryKey: ["github-status"],
    queryFn: () => api.get<{ connected: boolean }>("/auth/github/status"),
    retry: false,
  });
  const google = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get<{ connected: boolean }>("/auth/google/status"),
    retry: false,
  });
  const proactivity = useQuery({
    queryKey: [PROACTIVITY_STATUS_KEY],
    queryFn: () => api.get<{ enabled: boolean }>("/proactivity/status"),
    retry: false,
  });

  // Yanıt gelmeden hiçbir şey söylenmez: yükleme sırasında "eksik" göstermek
  // yanlış olurdu.
  if (settings.isLoading) return null;

  const profile = settings.data?.["opportunity.career_profile"] as
    { current_location?: string; authorized_countries?: string[] } | undefined;

  const coreSteps: SetupStep[] = [
    {
      id: "workspace",
      label: "Yerel çalışma alanı (API + veritabanı)",
      state: settings.isError ? "unknown" : "ready",
      href: "#/health",
    },
    {
      id: "vault",
      label: "Bilgi kasası (Vault)",
      state: vault.isError
        ? "unknown"
        : vault.data?.configured && vault.data.available && vault.data.readable
          ? "ready"
          : "missing",
      href: "#/settings?tab=brain",
    },
  ];

  const optionalSteps: SetupStep[] = [
    {
      id: "github",
      label: "GitHub",
      state: github.isError ? "unknown" : github.data?.connected ? "ready" : "missing",
      href: "#/settings?tab=integrations",
    },
    {
      id: "google",
      label: "Google Calendar",
      state: google.isError ? "unknown" : google.data?.connected ? "ready" : "missing",
      href: "#/settings?tab=integrations",
    },
    {
      id: "career",
      label: "Kariyer profili",
      state: !settings.data
        ? "unknown"
        : profile?.current_location || (profile?.authorized_countries?.length ?? 0) > 0
          ? "ready"
          : "missing",
      href: "#/settings?tab=career",
    },
    {
      id: "proactivity",
      label: "Proaktivite",
      state: proactivity.isError ? "unknown" : proactivity.data?.enabled ? "ready" : "missing",
      href: "#/settings?tab=notifications",
    },
  ];

  const coreReady = coreSteps.filter((step) => step.state === "ready").length;
  const optionalReady = optionalSteps.filter((step) => step.state === "ready").length;

  // Liste yalnız ÇEKİRDEK bir adım eksikse çizilir; isteğe bağlı entegrasyon
  // eksikliği tek başına bu yüzeyi açmaz.
  if (dismissed || coreReady === coreSteps.length) return null;

  return (
    <Section
      title="Kurulum"
      hint={`${coreReady}/${coreSteps.length} çekirdek adım`}
      action={
        <button
          type="button"
          aria-label="Kurulum listesini kapat"
          onClick={() => {
            try {
              globalThis.localStorage?.setItem(DISMISS_KEY, "1");
            } catch {
              // Depolama yoksa yalnız bu oturum için kapatılır.
            }
            setDismissed(true);
          }}
          className="text-muted transition hover:text-primary"
        >
          <X size={14} aria-hidden="true" />
        </button>
      }
      bodyClassName="stack-y-3"
    >
      <p className="text-meta text-muted">
        Çekirdek adımlar forkOS&apos;un çalışması için gerekir. Entegrasyonlar isteğe bağlıdır — eksik olmaları sorun
        değildir.
      </p>

      <ul className="stack-y-1.5">
        {coreSteps.map((step) => (
          <li key={step.id} className="flex items-center gap-2 text-meta">
            {step.state === "ready" ? (
              <Check size={14} className="shrink-0 text-ok" aria-hidden="true" />
            ) : step.state === "unknown" ? (
              <HelpCircle size={14} className="shrink-0 text-muted" aria-hidden="true" />
            ) : (
              <Circle size={14} className="shrink-0 text-muted" aria-hidden="true" />
            )}
            {step.state === "ready" ? (
              <span className="text-secondary">{step.label}</span>
            ) : (
              <a href={step.href} className={cx("text-primary hover:text-accent")}>
                {step.label}
              </a>
            )}
            {step.state === "unknown" && <Chip>doğrulanamadı</Chip>}
          </li>
        ))}
      </ul>

      <Disclosure
        summary={`İsteğe bağlı entegrasyonlar (${optionalReady}/${optionalSteps.length} bağlı) — kurulum için gerekli değil`}
      >
        <ul className="stack-y-1">
          {optionalSteps.map((step) => (
            <li key={step.id} className="flex items-center gap-2 text-meta">
              <span className="w-36 shrink-0 text-secondary">{step.label}</span>
              <Chip tone={step.state === "ready" ? "ok" : "neutral"}>
                {step.state === "ready" ? "bağlı" : step.state === "unknown" ? "bilinmiyor" : "bağlı değil"}
              </Chip>
              <a href={step.href} className="text-meta text-accent hover:underline">
                Ayarlar →
              </a>
            </li>
          ))}
        </ul>
      </Disclosure>
    </Section>
  );
}
