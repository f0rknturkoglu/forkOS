import { lazy } from "react";
import { FileText } from "lucide-react";
import { DocumentsWidget } from "./DocumentsWidget";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const DocumentsPage = lazy(() => import("./DocumentsPage").then((module) => ({ default: module.DocumentsPage })));

registerModule({
  id: "documents",
  title: "Belgeler",
  description: "Drive belgelerini ara, önizle ve son açılanlara hızlıca dön.",
  icon: FileText,
  routes: [{ path: "/documents", element: DocumentsPage }],
  todayWidgets: [
    {
      id: "documents.recent",
      title: "Belgeler",
      component: DocumentsWidget,
      region: "secondary",
      order: 45,
      defaultVisible: false,
    },
  ],
  commands: [{ id: "documents.open", label: "Drive belgelerini aç", run: () => navigate("/documents") }],
});
