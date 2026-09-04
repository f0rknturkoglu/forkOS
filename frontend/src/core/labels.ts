/**
 * Cekirdek etiket yardimcilari. Moduller buradan import eder; moduller arasi
 * dogrudan import (orn. health -> opportunity) yasak.
 */

/** "jobhunter:greenhouse:adyen" -> "adyen · greenhouse" */
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
  if (parts[0] === "jobhunter" && parts.length >= 3) {
    return `${parts.slice(2).join(":")} · ${parts[1]}`;
  }
  return source;
}
