import { lazy } from "react";
import { CalendarRange, ListChecks, Repeat } from "lucide-react";
import { OverdueTodosWidget } from "./OverdueTodosWidget";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { createTask, invalidateTaskWrite, readPlanTodayPreference } from "@/core/tasks";
import { emitGlobalToast } from "@/core/ui";

const TodoPage = lazy(() => import("./TodoPage").then((module) => ({ default: module.TodoPage })));
const WeeklyPlannerPage = lazy(() =>
  import("./WeeklyPlannerPage").then((module) => ({ default: module.WeeklyPlannerPage })),
);

registerModule({
  id: "todo",
  title: "Görevler",
  description: "Görev ve rutinlerini planla, haftalık planda gecikenleri yakala.",
  icon: ListChecks,
  routes: [
    { path: "/todos", element: TodoPage },
    // Sidebar cocuk sirasi (Plan alani): haftalik plan once, rutinler sonra.
    { path: "/planner", element: WeeklyPlannerPage, title: "Haftalık plan", icon: CalendarRange, navigation: "child" },
    { path: "/habits", element: TodoPage, title: "Rutinler", icon: Repeat, navigation: "child" },
  ],
  todayWidgets: [
    {
      id: "todo.overdue",
      title: "Geciken görevler",
      component: OverdueTodosWidget,
      // Durum seridi: "geciken" bir dikkat sinyalidir, gunluk plan degil.
      region: "rail",
      order: 15,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "todo.open", label: "Görevleri aç", run: () => navigate("/todos") },
    { id: "todo.routines", label: "Rutin görevleri aç", run: () => navigate("/habits") },
    { id: "planner.open", label: "Haftalık planı aç", run: () => navigate("/planner") },
    {
      id: "todo.quick",
      label: "Hızlı görev ekle",
      ask: { label: "Görev başlığı", placeholder: "Ne yapılacak?" },
      run: async (title) => {
        if (!title?.trim()) return;
        // Ortak intent (Faz 17): "bugune al" tercihi uygulanir, kullaniciyi
        // Todo sayfasina zorla tasimadan basari geri bildirimi verilir.
        await createTask({ title });
        invalidateTaskWrite();
        emitGlobalToast({
          message: readPlanTodayPreference() ? "Görev eklendi — bugüne planlandı" : "Görev eklendi",
          options: { tone: "ok", action: { label: "aç", run: () => navigate("/todos") } },
        });
      },
    },
  ],
});
