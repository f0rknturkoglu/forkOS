/**
 * Vault durum sözlüğü — `describeVaultState` öncelik sırası.
 *
 * Bilgi Kasası ve Ayarlar aynı Vault için aynı cümleyi söylemek zorundadır;
 * burada hem beş durumun karşılığı hem de öncelik (hata > yanıt var >
 * yapılandırılmamış > erişilemiyor > salt okunur > sağlıklı) sabitlenir.
 * Saf fonksiyon: ağ yok, fetch yok.
 */
import { describe, expect, it } from "vitest";
import { describeVaultState, type VaultState, type VaultStateKind, type VaultStatus } from "./obsidian";

/** Yalnız sınıflandırıcının baktığı alanlar; gerisi kararı değiştirmemeli. */
const health = (overrides: Partial<VaultStatus> = {}) => ({
  configured: true,
  available: true,
  writable: true,
  readable: true,
  diagnostic: null,
  ...overrides,
});

describe("describeVaultState", () => {
  it("sağlıklı Vault'ta hazır durumu ve ipucu yokluğunu bildirir", () => {
    expect(describeVaultState(health(), false)).toEqual({ kind: "ready", chip: "Vault bağlı ✓", hint: null });
  });

  it("salt okunur Vault'ta yazmanın kapalı olduğunu söyler", () => {
    const state = describeVaultState(health({ writable: false }), false);

    expect(state.kind).toBe("read_only");
    expect(state.chip).toBe("Vault bağlı · salt okunur");
    expect(state.hint).toMatch(/yakalama ve günlük not yazma kapalı/);
  });

  it("yapılandırılmamış Vault'ta runtime talimatı verir", () => {
    const state = describeVaultState(health({ configured: false, available: false, writable: false }), false);

    expect(state.kind).toBe("not_configured");
    expect(state.chip).toBe("Vault yapılandırılmamış");
    expect(state.hint).toMatch(/make up-obsidian/);
  });

  it("erişilemeyen Vault'ta sunucunun teşhisini taşır, yoksa kendi cümlesini kurar", () => {
    const diagnosed = describeVaultState(health({ available: false, diagnostic: "dizin bulunamadı" }), false);
    expect(diagnosed.kind).toBe("unavailable");
    expect(diagnosed.chip).toBe("Vault erişilemiyor");
    expect(diagnosed.hint).toBe("dizin bulunamadı");

    const blind = describeVaultState(health({ available: false }), false);
    expect(blind.hint).toMatch(/bind mount/);
  });

  it("okuma hatasında ve yanıt yokken okunamadı der", () => {
    const failed = describeVaultState(undefined, true);
    expect(failed.kind).toBe("unreadable");
    expect(failed.chip).toBe("Vault durumu okunamadı");
    expect(failed.hint).toMatch(/servisleri kontrol et/);

    const empty = describeVaultState(undefined, false);
    expect(empty).toEqual({ kind: "unreadable", chip: "Vault durumu okunamadı", hint: null });
  });

  it("okuma hatası elde durum varken bile kazanır", () => {
    // Elde bayat bir "hazır" yanıtı olsa da istek düştüyse gösterilen o değil.
    expect(describeVaultState(health(), true).kind).toBe("unreadable");
    expect(describeVaultState(health({ configured: false }), true).kind).toBe("unreadable");
  });

  it("yapılandırılmamış, erişilemiyor ve salt okunur durumlarına göre önce gelir", () => {
    // `available`/`writable` bayrakları yanıltıcı olsa bile asıl eksik yapılandırmadır.
    const state = describeVaultState(health({ configured: false, available: false, writable: false }), false);

    expect(state.kind).toBe("not_configured");
  });

  it("erişilemiyor, salt okunur durumuna göre önce gelir", () => {
    const state = describeVaultState(health({ available: false, writable: false }), false);

    expect(state.kind).toBe("unavailable");
  });

  it("sözlükteki her tür gerçek bir yanıttan üretilebiliyor ve dolu etiket taşıyor", () => {
    // Ölü sözlük değeri bırakma: `VaultStateKind`'ın her elemanı bir üretim
    // yoluna bağlı olmalı, yoksa Ayarlar/Ayarlar ekranı boş chip çizer.
    const kinds: VaultStateKind[] = ["ready", "read_only", "not_configured", "unavailable", "unreadable"];
    const states: VaultState[] = [
      describeVaultState(health(), false),
      describeVaultState(health({ writable: false }), false),
      describeVaultState(health({ configured: false }), false),
      describeVaultState(health({ available: false }), false),
      describeVaultState(undefined, false),
    ];

    expect(states.map((state) => state.kind)).toEqual(kinds);
    for (const state of states) expect(state.chip.trim()).not.toBe("");
  });
});
