import type { ComponentType } from "react";
import { SourceHealthWidget } from "./SourceHealthWidget";
import { RssHealthWidget } from "./RssHealthWidget";
import { BackupHealthWidget } from "./BackupHealthWidget";
import { ServiceHealthWidget } from "./ServiceHealthWidget";
import { SetupChecklist } from "../SetupChecklist";

/**
 * Dashboard widget'lari. Yeni widget = bileseni yaz, bu listeye ekle
 * (yer imi: "moduler ekleme" -- sayfa ve Today otomatik beslenir).
 */
export const WIDGETS: { name: string; component: ComponentType }[] = [
  // Kurulum listesi yalnız EKSİK bir adım varsa çizilir (kendi içinde null döner):
  // kurulumu tamamlanmış kullanıcı bu yüzeyi hiç görmez.
  { name: "kurulum", component: SetupChecklist },
  { name: "kaynak-sagligi", component: SourceHealthWidget },
  { name: "rss-sagligi", component: RssHealthWidget },
  { name: "yedekleme", component: BackupHealthWidget },
  { name: "servis", component: ServiceHealthWidget },
];
