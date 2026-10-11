import { Info } from "lucide-react";
import { IconButton } from "@/core/ui";
import { openGuide } from "./experience";
export function PageInfoButton() {
  return (
    <IconButton
      title="Bu sayfa hakkında bilgi ve rehberler"
      onClick={openGuide}
      className="page-info-button rounded-full"
    >
      <Info size={14} />
    </IconButton>
  );
}
