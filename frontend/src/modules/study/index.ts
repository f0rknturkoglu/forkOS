import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { StudyPage } from "./StudyPage";
import { StudyWidget } from "./StudyWidget";

registerModule({
  id: "study", title: "Study",
  routes: [{ path: "/study", element: StudyPage }],
  todayWidgets: [StudyWidget],
  commands: [{ id: "study.open", label: "Çalışma ağacını aç", run: () => navigate("/study") }],
});
