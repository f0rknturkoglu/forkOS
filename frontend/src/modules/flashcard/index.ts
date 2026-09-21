import { lazy } from "react";
import { Layers } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { openCapture } from "@/core/CaptureDialog";
import { TodayFlashcardWidget } from "./TodayFlashcardWidget";

const FlashcardPage = lazy(() => import("./FlashcardPage").then((module) => ({ default: module.FlashcardPage })));

registerModule({
  id: "flashcard",
  title: "Kartlar",
  description: "Kart desteleriyle aralıklı tekrar yap, bilgiyi kalıcı hale getir.",
  icon: Layers,
  routes: [{ path: "/flashcard", element: FlashcardPage }],
  todayWidgets: [
    // Sag sutun: gunun odak/plan blogunun yaninda "bugun tekrar" hatirlaticisi.
    {
      id: "flashcard.due",
      title: "Kart tekrarı",
      component: TodayFlashcardWidget,
      slot: "right",
      order: 25,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "flashcard.open", label: "Kartları aç", run: () => navigate("/flashcard") },
    {
      id: "flashcard.review_due",
      label: "Bugünün kart tekrarlarını başlat",
      run: () => navigate("/flashcard?review=due"),
    },
    { id: "flashcard.new_card", label: "Hızlı kart ekle", run: () => openCapture({ kind: "flashcard" }) },
    {
      id: "flashcard.cram_missed",
      label: "Zayıf noktaları / yanlışları tekrar et",
      run: () => navigate("/flashcard?review=missed"),
    },
  ],
});
