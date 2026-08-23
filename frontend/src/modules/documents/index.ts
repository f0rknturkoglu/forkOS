import { lazy } from "react";
import { FileText } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const DocumentsPage = lazy(() => import("./DocumentsPage").then((module) => ({ default: module.DocumentsPage })));

registerModule({ id: "documents", title: "Belgeler", icon: FileText, group: "capture", routes: [{ path: "/documents", element: DocumentsPage }], commands: [{ id: "documents.open", label: "Drive belgelerini aç", run: () => navigate("/documents") }] });
