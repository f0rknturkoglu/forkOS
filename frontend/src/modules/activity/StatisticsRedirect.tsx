import { useEffect } from "react";
import { navigate } from "@/app/router";

/**
 * Eski `#/statistics` rotasi. Istatistikler modulu Etkinlik & Ritim ile
 * birlesti; eski yer imleri ve paylasilan baglantilar kirilmasin diye burada
 * kalici yonlendirme var (gecmisi geri tusunda biriktirmemek icin replace).
 */
export function StatisticsRedirect() {
  useEffect(() => {
    navigate("/activity", { replace: true });
  }, []);
  return <div className="p-6 text-body text-muted">İstatistikler artık Etkinlik & Ritim sayfasında…</div>;
}
