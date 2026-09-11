/**
 * Cekirdek etiket yardimcilari. Moduller buradan import eder; moduller arasi
 * dogrudan import (orn. health -> opportunity) yasak.
 */

/** "jobhunter:greenhouse:adyen" -> "adyen · greenhouse" · "jobhunter:eures" -> "eures" */
export function sourceLabel(source: string): string {
  if (source === "manual") {
    return "Manuel Eklenen";
  }
  if (source === "extension") {
    return "Eklenti";
  }
  if (source === "custom") {
    return "Özel İlan";
  }
  const parts = source.split(":");
  if (parts[0] === "jobhunter") {
    // Şirket/portal kimliği tek parçaysa ("jobhunter:eures") yalnızca o ad
    // gösterilir; "jobhunter:" öneki kullanıcıya hiçbir şey söylemez.
    if (parts.length === 2) return parts[1];
    if (parts.length >= 3) return `${parts.slice(2).join(":")} · ${parts[1]}`;
  }
  return source;
}
