import { lazy } from "react";
import { ClipboardCheck } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ReviewWidget } from "./ReviewWidget";

const DailyReviewPage = lazy(() => import("./ReviewPage").then((module) => ({ default: module.DailyReviewPage })));
const WeeklyReviewPage = lazy(() => import("./ReviewPage").then((module) => ({ default: module.WeeklyReviewPage })));
const MonthlyReviewPage = lazy(() => import("./ReviewPage").then((module) => ({ default: module.MonthlyReviewPage })));
const YearlyReviewPage = lazy(() => import("./ReviewPage").then((module) => ({ default: module.YearlyReviewPage })));

registerModule({
  id: "review",
  title: "Değerlendirme",
  description: "Günlük ve haftalık değerlendirmelerle ilerlemeni gözden geçir.",
  icon: ClipboardCheck,
  routes: [
    { path: "/review/weekly", element: WeeklyReviewPage },
    { path: "/review/monthly", element: MonthlyReviewPage, navigation: "hidden" },
    { path: "/review/yearly", element: YearlyReviewPage, navigation: "hidden" },
    { path: "/review/daily", element: DailyReviewPage },
  ],
  todayWidgets: [
    {
      id: "review.widget",
      title: "Değerlendirme",
      component: ReviewWidget,
      order: 80,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "review.weekly", label: "Haftalık değerlendirmeyi aç", run: () => navigate("/review/weekly") },
    { id: "review.daily", label: "Günlük değerlendirmeyi aç", run: () => navigate("/review/daily") },
  ],
});
