import type { ComponentType } from "react";
import { SourceHealthWidget } from "./SourceHealthWidget";
import { RssHealthWidget } from "./RssHealthWidget";
import { BackupHealthWidget } from "./BackupHealthWidget";

/**
 * Dashboard widget'lari. Yeni widget = bileseni yaz, bu listeye ekle
 * (yer imi: "moduler ekleme" -- sayfa ve Today otomatik beslenir).
 */
export const WIDGETS: { name: string; component: ComponentType }[] = [
  { name: "kaynak-sagligi", component: SourceHealthWidget },
  { name: "rss-sagligi", component: RssHealthWidget },
  { name: "yedekleme", component: BackupHealthWidget },
];
