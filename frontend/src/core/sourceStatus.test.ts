/**
 * Durum semantiği sözleşmesi (tek kaynak).
 *
 * Buradaki testler ürün dürüstlüğünü korur: `disabled` kırmızı olamaz, tek
 * boş koşu "sorun" sayılamaz, üst üste üç boş koşu sayılır, bilinmeyen durum
 * yeşile dönmez ve genel durum bir alt sistem bilinmiyorken "sağlıklı" demez.
 */
import { describe, expect, it } from "vitest";
import {
  circuitView,
  errorPreview,
  errorKindLabel,
  errorKindTone,
  feedStateView,
  healthSummaryLabel,
  isProblem,
  overallState,
  overallView,
  problemReasons,
  runStateView,
  sourceClassLabel,
  sourceKindLabel,
} from "./sourceStatus";

describe("runStateView", () => {
  it("kullanıcıya Türkçe etiket verir; ham enum sızmaz", () => {
    expect(runStateView("ok").label).toBe("sağlıklı");
    expect(runStateView("partial").label).toBe("kısmi");
    expect(runStateView("error").label).toBe("hata");
    expect(runStateView("running").label).toBe("çekiliyor");
    expect(runStateView("queued").label).toBe("sırada");
    expect(runStateView("abandoned").label).toBe("yarım kaldı");
    expect(runStateView("empty").label).toBe("yeni kayıt yok");
    expect(runStateView(undefined).label).toBe("bilinmiyor");
    // Bilinmeyen bir durum uydurulmaz, olduğu gibi gösterilir.
    expect(runStateView("weird_state").label).toBe("weird_state");
  });

  it("disabled/kapalı asla hata rengi değildir", () => {
    const disabled = runStateView("disabled");
    expect(disabled.tone).toBe("neutral");
    expect(disabled.attention).toBe(false);
  });

  it("yalnız gerçek problem durumları ilgi ister", () => {
    expect(runStateView("ok").attention).toBe(false);
    expect(runStateView("empty").attention).toBe(false);
    expect(runStateView("running").attention).toBe(false);
    expect(runStateView("queued").attention).toBe(false);
    expect(runStateView("new").attention).toBe(false);
    expect(runStateView("unknown").attention).toBe(false);
    expect(runStateView("partial").attention).toBe(true);
    expect(runStateView("error").attention).toBe(true);
    expect(runStateView("abandoned").attention).toBe(true);
  });
});

describe("isProblem — eşikler backend sözleşmesi", () => {
  it("tek boş koşu sorun değildir, üst üste üç boş koşu sorundur", () => {
    expect(isProblem({ last_status: "empty", consecutive_empty: 1 })).toBe(false);
    expect(isProblem({ last_status: "empty", consecutive_empty: 2 })).toBe(false);
    expect(isProblem({ last_status: "empty", consecutive_empty: 3 })).toBe(true);
    expect(isProblem({ last_status: "empty", consecutive_empty: 9 })).toBe(true);
  });

  it("hata ve açık devre sorundur; sağlıklı ve kapalı değildir", () => {
    // Hata sınıfı bilinmese de "son koşu hata" tek başına sorundur.
    expect(isProblem({ last_status: "error" })).toBe(true);
    expect(isProblem({ last_status: "error", last_error_kind: "http_429" })).toBe(true);
    expect(isProblem({ circuit_open: true })).toBe(true);
    expect(isProblem({ last_status: "ok", consecutive_empty: 0 })).toBe(false);
    expect(isProblem({ last_status: "disabled" })).toBe(false);
    expect(isProblem(null)).toBe(false);
  });

  it("nedenleri insan diline çevirir", () => {
    expect(problemReasons({ circuit_open: true })).toEqual(["devre açık"]);
    expect(problemReasons({ last_status: "error", last_error_kind: "http_429" })).toEqual(["son koşu hata (429)"]);
    expect(problemReasons({ last_status: "empty", consecutive_empty: 4 })).toEqual(["4 koşum boş"]);
    expect(problemReasons({ circuit_open: true, last_status: "error", consecutive_empty: 3 })).toEqual([
      "devre açık",
      "son koşu hata",
      "3 koşum boş",
    ]);
  });
});

describe("hata sınıfı okunabilirliği", () => {
  it("ham enum yerine kısa etiket verir", () => {
    expect(errorKindLabel("http_429")).toBe("429");
    expect(errorKindLabel("http_5xx")).toBe("5xx");
    expect(errorKindLabel("http_403")).toBe("403");
    expect(errorKindLabel("tls")).toBe("TLS");
    expect(errorKindLabel("dns")).toBe("DNS");
    expect(errorKindLabel("timeout")).toBe("zaman aşımı");
    expect(errorKindLabel("parser")).toBe("ayrıştırma");
    expect(errorKindLabel("circuit_open")).toBe("devre açık");
    expect(errorKindLabel(null)).toBeNull();
    // Bilinmeyen sınıf uydurulmaz.
    expect(errorKindLabel("new_kind")).toBe("new_kind");
  });

  it("yine denenebilir sınıflar amber, kalıcı olanlar kırmızı", () => {
    expect(errorKindTone("http_429")).toBe("warn");
    expect(errorKindTone("timeout")).toBe("warn");
    expect(errorKindTone("parser")).toBe("danger");
    expect(errorKindTone("circuit_open")).toBe("danger");
    expect(errorKindTone(null)).toBe("neutral");
  });
});

describe("circuitView", () => {
  it("yalnız açık devrede rozet üretir", () => {
    expect(circuitView(true)).toEqual({ label: "devre açık", tone: "danger", attention: true });
    expect(circuitView(false)).toBeNull();
    expect(circuitView(undefined)).toBeNull();
  });
});

describe("kaynak sınıfı ve türü", () => {
  it("sınıf etiketleri korunur", () => {
    expect(sourceClassLabel("critical")).toBe("Kritik");
    expect(sourceClassLabel("normal")).toBe("Normal");
    expect(sourceClassLabel("slow_optin")).toBe("Yavaş / isteğe bağlı");
    expect(sourceClassLabel(null)).toBeNull();
  });

  it("tür etiketleri", () => {
    expect(sourceKindLabel("job")).toBe("İş ilanı");
    expect(sourceKindLabel("announcement")).toBe("Duyuru");
  });
});

describe("RSS besleme durumu", () => {
  it("bilerek kapatılan besleme bozuk DEĞİLDİR", () => {
    const view = feedStateView({ active: false, error_count: 0, last_fetched_at: "2026-09-01T00:00:00Z" });
    expect(view.label).toBe("kapalı");
    expect(view.tone).toBe("neutral");
    expect(view.attention).toBe(false);
  });

  it("hata birikmiş besleme kırmızıdır", () => {
    const view = feedStateView({ active: true, error_count: 3, last_fetched_at: "2026-09-01T00:00:00Z" });
    expect(view.tone).toBe("danger");
    expect(view.attention).toBe(true);
  });

  it("hiç çekilmemiş besleme nötrdür, boş dönen amber ama ilgi istemez", () => {
    expect(feedStateView({ active: true, error_count: 0, last_fetched_at: null }).label).toBe("çekilmedi");
    const empty = feedStateView({ active: true, error_count: 0, last_status: "empty", last_fetched_at: "x" });
    expect(empty.label).toBe("yeni kayıt yok");
    expect(empty.attention).toBe(false);
  });

  it("veri yoksa bilinmiyor der", () => {
    expect(feedStateView(undefined).label).toBe("bilinmiyor");
  });
});

describe("özet ve genel durum", () => {
  it("özet cümlesi bilinmeyen durumda 'sağlıklı' demez", () => {
    expect(healthSummaryLabel({ total: 42, healthy: 42, attention: 0 })).toBe("42 sağlıklı");
    expect(healthSummaryLabel({ total: 42, healthy: 40, attention: 2 })).toBe("40 sağlıklı · 2 ilgi istiyor");
    expect(healthSummaryLabel({ total: 0, healthy: 0, attention: 0 })).toBe("kayıt yok");
    expect(healthSummaryLabel({ total: 42, healthy: 0, attention: 0, unknown: true })).toBe("durum bilinmiyor");
  });

  it("bilinmeyen alt sistem genel durumu yeşile çevirmez", () => {
    expect(overallState({ unknown: true, attention: false })).toBe("partly_unknown");
    expect(overallState({ unknown: true, attention: true })).toBe("attention");
    expect(overallState({ unknown: false, attention: false })).toBe("healthy");
    expect(overallView("partly_unknown").label).toBe("Durum kısmen bilinmiyor");
    expect(overallView("healthy").tone).toBe("ok");
    expect(overallView("attention").attention).toBe(true);
  });
});

describe("errorPreview — liste görünümü", () => {
  it("sınıf ön ekini atar, satırı tek satıra indirir", () => {
    expect(errorPreview("ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] cert failed")).toBe(
      "[SSL: CERTIFICATE_VERIFY_FAILED] cert failed",
    );
    expect(errorPreview("TimeoutError: forkjob_core:eures exceeded 900s budget")).toBe(
      "forkjob_core:eures exceeded 900s budget",
    );
    expect(errorPreview("satır bir\nsatır iki")).toBe("satır bir satır iki");
  });

  it("uzun metni sınırlar, kısa metne dokunmaz", () => {
    const long = "x".repeat(400);
    const out = errorPreview(long, 40);
    expect(out).not.toBeNull();
    expect((out ?? "").length).toBeLessThanOrEqual(40);
    expect(out?.endsWith("…")).toBe(true);
    expect(errorPreview("kısa hata")).toBe("kısa hata");
  });

  it("boş girdide null döner (uydurma metin yok)", () => {
    expect(errorPreview(null)).toBeNull();
    expect(errorPreview("   ")).toBeNull();
  });
});
