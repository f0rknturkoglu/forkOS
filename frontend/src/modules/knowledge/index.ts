import { lazy } from "react";
import { BookOpen } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { openCapture } from "@/core/CaptureDialog";
import { getVaultSearchUri, getVaultStatus, openObsidianUri } from "@/core/obsidian";

const KnowledgePage = lazy(() => import("./KnowledgePage").then((module) => ({ default: module.KnowledgePage })));

/**
 * Bilgi modulu = Vault köprüsü. forkOS'ta not editörü, liste, tuval ya da graf
 * YOKTUR; burada yalnız kasaya giden yollar ve indeks durumu gösterilir.
 *
 * Rota bilinçli olarak eski `/notes` yolunda kalır: geçmiş Aktivite kayıtları,
 * yer imleri ve paylaşılmış bağlantılar `?focus=<forkos-uuid>` derin bağlantısıyla
 * çalışmaya devam etsin diye (bkz. KnowledgePage focus bölümü).
 */
registerModule({
  id: "knowledge",
  title: "Bilgi",
  description: "Notlar ve uzun süreli bilgi f0rknbrain Obsidian Vault'ta yaşar; buradan aç ve ara.",
  icon: BookOpen,
  routes: [{ path: "/notes", element: KnowledgePage }],
  commands: [
    { id: "knowledge.open", label: "Bilgi kasasını aç", run: () => navigate("/notes") },
    {
      id: "knowledge.capture",
      label: "Hızlı not yakala",
      // Yakalama kutusu tur secili acilir: "not" bir bilgi notudur, görev degil.
      run: () => openCapture({ kind: "note" }),
    },
    {
      id: "knowledge.daily",
      label: "Bugünün günlük notunu aç",
      // Gunluk notun sahibi Obsidian'in kendisidir; URI sunucudan gelir.
      run: async () => {
        const status = await getVaultStatus();
        if (status.daily_uri) openObsidianUri(status.daily_uri);
      },
    },
    {
      id: "knowledge.search",
      label: "Vault'ta ara",
      ask: { label: "Vault arama sorgusu", placeholder: "ör. forkOS mimari" },
      run: async (query) => {
        if (!query?.trim()) return;
        const { uri } = await getVaultSearchUri(query.trim());
        openObsidianUri(uri);
      },
    },
  ],
});
