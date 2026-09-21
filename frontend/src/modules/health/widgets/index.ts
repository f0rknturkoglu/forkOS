import type { ComponentType } from "react";
import { SourceHealthWidget } from "./SourceHealthWidget";
import { RssHealthWidget } from "./RssHealthWidget";
import { BackupHealthWidget } from "./BackupHealthWidget";
import { ServiceHealthWidget } from "./ServiceHealthWidget";

/**
 * "Ayrıntılı sağlık" grubunun kartları.
 *
 * Sistem Durumu sayfası artık tek bir gelişigüzel ızgara değil (§28): önce
 * "Genel bakış" özeti, sonra yalnız gösterilecek bir şey varsa "İlgi
 * gerekenler", en sonda bu ayrıntılı kartlar gelir. Sağlıklı envanter burada
 * listelenmez (§68) — kaynak kataloğunun tamamı kanonik `/sources` sayfasıdır.
 *
 * Yeni widget = bileşeni yaz, bu listeye ekle (modüler ekleme).
 */
export const DETAIL_WIDGETS: { name: string; component: ComponentType }[] = [
  { name: "kaynak-sagligi", component: SourceHealthWidget },
  { name: "rss-sagligi", component: RssHealthWidget },
  { name: "yedekleme", component: BackupHealthWidget },
  { name: "servis", component: ServiceHealthWidget },
];
