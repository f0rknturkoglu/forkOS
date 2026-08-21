import { FileText } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { DocumentsPage } from "./DocumentsPage";

registerModule({ id: "documents", title: "Belgeler", icon: FileText, group: "capture", routes: [{ path: "/documents", element: DocumentsPage }], commands: [{ id: "documents.open", label: "Drive belgelerini aç", run: () => navigate("/documents") }] });
