import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Circle, X } from "lucide-react";
import { api } from "@/core/api";
import { getVaultStatus } from "@/core/obsidian";
import { PROACTIVITY_STATUS_KEY } from "@/core/proactivity";
import { Section, cx } from "@/core/ui";
import type { AppSettings } from "@/core/types";

/**
 * Kurulum kontrol listesi (P6 §53).
 *
 * Karmaşık bir onboarding SİHİRBAZI değildir: yalnız eksik olanı gösterir.
 * Kurulum tamamlanmış kullanıcı (bu uygulamanın gerçek kullanıcısı) bu yüzeyi
 * HİÇ görmez; günlük akışa karışmaz. Yeni bir kurulumda Sistem Durumu
 * sayfasında yol gösterir, tamamlanınca veya kapatılınca kaybolur.
 *
 * Tüm durumlar mevcut uçlardan okunur; yeni bir "setup" ucu yoktur.
 */

const DISMISS_KEY = "forkos.setup.dismissed";

interface SetupStep {
  id: string;
  label: string;
  done: boolean;
  /** Eksikse gidilecek yer. */
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
  const vault = useQuery({
    queryKey: ["obsidian-status"],
    queryFn: getVaultStatus,
    retry: false,
  });
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
  // Kariyer profili ayarlarda saklanır: kabuğun zaten çektiği anahtarı kullanır.
  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
    retry: false,
  });
  const proactivity = useQuery({
    queryKey: [PROACTIVITY_STATUS_KEY],
    queryFn: () => api.get<{ enabled: boolean }>("/proactivity/status"),
    retry: false,
  });

  const profile = settings.data?.["opportunity.career_profile"] as
    { current_location?: string; authorized_countries?: string[] } | undefined;

  // Yerel veritabanı: bu sayfa render edildiyse API ayakta demektir.
  const steps: SetupStep[] = [
    { id: "database", label: "Yerel veritabanı", done: true, href: "#/health" },
    {
      id: "vault",
      label: "Bilgi kasası (Vault)",
      done: Boolean(vault.data?.configured && vault.data.available && vault.data.readable),
      href: "#/notes",
    },
    { id: "github", label: "GitHub", done: Boolean(github.data?.connected), href: "#/settings?tab=integrations" },
    {
      id: "google",
      label: "Google (Drive)",
      done: Boolean(google.data?.connected),
      href: "#/settings?tab=integrations",
    },
    {
      id: "career",
      label: "Kariyer profili",
      done: Boolean(profile?.current_location || (profile?.authorized_countries?.length ?? 0) > 0),
      href: "#/settings?tab=career",
    },
    {
      id: "proactivity",
      label: "Proaktivite",
      done: Boolean(proactivity.data?.enabled),
      href: "#/settings?tab=notifications",
    },
  ];

  const remaining = steps.filter((step) => !step.done);
  if (dismissed || remaining.length === 0) return null;

  return (
    <Section
      title="Kurulum"
      hint={`${steps.length - remaining.length}/${steps.length}`}
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
          <X size={14} />
        </button>
      }
    >
      <ul className="space-y-1.5">
        {steps.map((step) => (
          <li key={step.id} className="flex items-center gap-2 text-meta">
            {step.done ? (
              <Check size={14} className="shrink-0 text-ok" aria-hidden="true" />
            ) : (
              <Circle size={14} className="shrink-0 text-muted" aria-hidden="true" />
            )}
            {step.done ? (
              <span className="text-secondary">{step.label}</span>
            ) : (
              <a href={step.href} className={cx("text-primary hover:text-accent")}>
                {step.label}
              </a>
            )}
          </li>
        ))}
      </ul>
    </Section>
  );
}
