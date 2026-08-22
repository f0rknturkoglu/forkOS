import { ClipboardCheck } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { DailyReviewPage, WeeklyReviewPage } from "./ReviewPage";
import { ReviewWidget } from "./ReviewWidget";

registerModule({ id: "review", title: "Değerlendirme", icon: ClipboardCheck, group: "track", routes: [
  { path: "/review/weekly", element: WeeklyReviewPage },
  { path: "/review/daily", element: DailyReviewPage },
], todayWidgets: [{ component: ReviewWidget, zone: "rhythm", slot: "left", order: 80 }], commands: [
  { id: "review.weekly", label: "Haftalık değerlendirmeyi aç", run: () => navigate("/review/weekly") },
  { id: "review.daily", label: "Günlük değerlendirmeyi aç", run: () => navigate("/review/daily") },
] });
