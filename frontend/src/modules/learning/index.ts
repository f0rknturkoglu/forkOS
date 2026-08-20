import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { LearningPage } from "./LearningPage";

registerModule({ id: "learning", title: "Learning", routes: [{ path: "/learning", element: LearningPage }], commands: [{ id: "learning.open", label: "Kurs, kitap ve öğrenme kuyruğunu aç", run: () => navigate("/learning") }] });
