/**
 * localStorage erisimi ve `lifeos.*` -> `forkos.*` gocu.
 *
 * Eski kurulumlarda tercihler `lifeos.*` anahtarlari altinda duruyor. Anahtar
 * adlarini degistirmek veri kaybettirmemeli: `readStored` once yeni anahtari
 * okur, bulamazsa eski anahtari okur ve yeni ada KOPYALAR. Goc boylece tek
 * seferde olur; sonraki okumalar legacy anahtara hic bakmaz.
 *
 * Yeni anahtar yazan her yer bu yardimciyi kullanir; dogrudan
 * `localStorage.getItem("forkos.…")` cagrisi iki sozlesme dogurur.
 */

const STORAGE_PREFIX = "forkos.";

/** Eski onek; yalnizca goc okumasinda kullanilir. */
const LEGACY_PREFIX = "lifeos.";

export function readStored(key: string): string | null {
  const current = localStorage.getItem(STORAGE_PREFIX + key);
  if (current !== null) return current;
  const legacy = localStorage.getItem(LEGACY_PREFIX + key);
  if (legacy === null) return null;
  localStorage.setItem(STORAGE_PREFIX + key, legacy);
  return legacy;
}

export function writeStored(key: string, value: string): void {
  localStorage.setItem(STORAGE_PREFIX + key, value);
}

export function removeStored(key: string): void {
  localStorage.removeItem(STORAGE_PREFIX + key);
  localStorage.removeItem(LEGACY_PREFIX + key);
}
