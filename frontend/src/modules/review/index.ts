import { lazy } from "react";
import { ClipboardCheck } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ReviewWidget } from "./ReviewWidget";

const DailyReviewPage = lazy(() => import("./ReviewPage").then((module) => ({ default: module.DailyReviewPage })));
const WeeklyReviewPage = lazy(() => import("./ReviewPage").then((module) => ({ default: module.WeeklyReviewPage })));

registerModule({
  id: "review",
  title: "Değerlendirme",
  icon: ClipboardCheck,
  hidden: true,
  routes: [
    { path: "/review/weekly", element: WeeklyReviewPage },
    { path: "/review/daily", element: DailyReviewPage },
  ],
  todayWidgets: [{ id: "review.widget", title: "Değerlendirme", component: ReviewWidget, slot: "left", order: 80 }],
  commands: [
    { id: "review.weekly", label: "Haftalık değerlendirmeyi aç", run: () => navigate("/review/weekly") },
    { id: "review.daily", label: "Günlük değerlendirmeyi aç", run: () => navigate("/review/daily") },
  ],
});
