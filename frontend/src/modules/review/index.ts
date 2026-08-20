import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { DailyReviewPage, WeeklyReviewPage } from "./ReviewPage";

registerModule({ id: "review", title: "Reviews", routes: [
  { path: "/review/weekly", element: WeeklyReviewPage },
  { path: "/review/daily", element: DailyReviewPage },
], commands: [
  { id: "review.weekly", label: "Weekly Review'u ac", run: () => navigate("/review/weekly") },
  { id: "review.daily", label: "Daily Review'u ac", run: () => navigate("/review/daily") },
] });
