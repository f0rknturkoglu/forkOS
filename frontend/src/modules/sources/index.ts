/**
 * Kaynak operasyonları modülü.
 *
 * `/sources` rotası Sistem alanında "Kaynaklar" satırı olarak görünür
 * (`core/navigation.ts` → system.moduleIds). Aynı yüzeyi Kariyer > Kaynaklar
 * sekmesi de "career" çerçevesiyle kullanır; ikinci bir uygulama yoktur.
 */
import { lazy } from "react";
import { Radio } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";

const SourcesPage = lazy(() => import("./SourcesPage").then((module) => ({ default: module.SourcesPage })));

registerModule({
  id: "sources",
  title: "Kaynaklar",
  description: "Kaynak kataloğu, sağlık durumu, koşu geçmişi ve disk önbelleği.",
  icon: Radio,
  routes: [{ path: "/sources", element: SourcesPage, title: "Kaynaklar" }],
  commands: [{ id: "sources.open", label: "Kaynakları aç", run: () => navigate("/sources") }],
});
