import { ClipboardCheck } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { DailyReviewPage, WeeklyReviewPage } from "./ReviewPage";

registerModule({ id: "review", title: "Değerlendirme", icon: ClipboardCheck, group: "track", routes: [
  { path: "/review/weekly", element: WeeklyReviewPage },
  { path: "/review/daily", element: DailyReviewPage },
], commands: [
  { id: "review.weekly", label: "Haftalık değerlendirmeyi aç", run: () => navigate("/review/weekly") },
  { id: "review.daily", label: "Günlük değerlendirmeyi aç", run: () => navigate("/review/daily") },
] });
