/** Public per-item outcome vocabulary, independent of aggregate queue counts. */
export const DELIVERY_LABELS = Object.freeze({
  saved: "Kaydedildi",
  already_present: "Zaten kayıtlı · aynı sonuç doğrulandı",
  queued_offline: "Çevrimdışı kuyruğa alındı",
  retry_pending: "Yeniden deneme bekliyor",
  rejected: "Sunucu reddetti · kayıt hata listesinde korunuyor",
  invalid_input: "Girdi geçersiz",
  permanent_conflict: "Kimlik/içerik çakışması · düzeltme gerekli",
  vault_unavailable: "Vault kullanılamıyor · kayıt kuyrukta korunuyor",
  unknown_delivery:
    "Teslim sonucu bilinmiyor · aynı kimlikle yeniden kontrol edilecek",
});
export function deliveryText(result) {
  const receipt = result?.capture;
  return `${DELIVERY_LABELS[receipt?.state] ?? "Sonuç doğrulanamadı"}${receipt?.message ? ": " + receipt.message : ""}`;
}
