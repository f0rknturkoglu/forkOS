import { lazy } from "react";
import { Layers } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const FlashcardPage = lazy(() => import("./FlashcardPage").then((module) => ({ default: module.FlashcardPage })));

registerModule({
  id: "flashcard",
  title: "Kartlar",
  icon: Layers,
  group: "track",
  routes: [{ path: "/flashcard", element: FlashcardPage }],
  commands: [
    {
      id: "flashcard.open",
      label: "Kartları aç — tekrar oturumu başlat",
      run: () => navigate("/flashcard"),
    },
  ],
});
