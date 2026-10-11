/**
 * Cekirdek etiket yardimcilari. Moduller buradan import eder; moduller arasi
 * dogrudan import (orn. health -> opportunity) yasak.
 */

/** "forkjob_core:greenhouse:adyen" -> "adyen · greenhouse" · "forkjob_core:eures" -> "eures" */
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
  if (parts[0] === "news") {
    const names: Record<string, string> = {
      "hacker-news": "Hacker News",
      "github-trending": "GitHub · Yeni ve Popüler",
      "huggingface-papers": "Hugging Face Papers",
      reddit: "Reddit",
    };
    return names[parts[1]] || source;
  }
  if (parts[0] === "careerops") {
    if (parts[1] === "boards") return "career-ops · açık panolar";
    if (parts[1] === "companies") return "career-ops · takip edilen şirketler";
    return `career-ops · ${parts.slice(1).join(":")}`;
  }
  if (parts[0] === "forkjob_core") {
    // Şirket/portal kimliği tek parçaysa ("forkjob_core:eures") yalnızca o ad
    // gösterilir; "forkjob_core:" öneki kullanıcıya hiçbir şey söylemez.
    if (parts.length === 2) return parts[1];
    if (parts.length >= 3) return `${parts.slice(2).join(":")} · ${parts[1]}`;
  }
  return source;
}
