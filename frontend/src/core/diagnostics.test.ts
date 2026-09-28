/**
 * Tanılama paketi biçimi sözleşmesi.
 *
 * Paketin amacı: kullanıcı tek tıkla, sır sızdırmadan, bir kodlama ajanının
 * doğrudan kullanabileceği bağlamı paylaşabilsin. Bu yüzden testler içerik
 * SÖZLEŞMESİNİ doğrular: kimlik var, hata sınıfı var, devre durumu var, son
 * başarı var, bilinmeyen bölüm ATLANMAZ ve sır alanları GİRMEZ.
 */
import { describe, expect, it } from "vitest";
import {
  formatSourceDiagnostics,
  formatSystemDiagnostics,
  type SourceProblemDiagnostic,
  type SystemDiagnosticsInput,
} from "./diagnostics";

const GENERATED = "2026-09-22T10:00:00.000Z";

const PROBLEM: SourceProblemDiagnostic = {
  source: "forkjob_core:linkedin",
  label: "LinkedIn Guest",
  source_class: "slow_optin",
  kind: "job",
  status: "error",
  error_kind: "http_429",
  circuit_open: true,
  consecutive_failures: 5,
  consecutive_empty: 0,
  last_run_at: "2026-09-22T09:40:00.000Z",
  last_success_at: "2026-09-22T06:15:00.000Z",
  last_new_content_at: "2026-09-22T06:15:00.000Z",
  parser_version: "3",
  last_error: "429 Too Many Requests",
};

describe("formatSourceDiagnostics", () => {
  it("ajanın ihtiyaç duyduğu kimlik ve sınıflandırma alanlarını taşır", () => {
    const bundle = formatSourceDiagnostics({
      generated_at: GENERATED,
      scope: "opportunity",
      source_count: 48,
      problems: [PROBLEM],
    });

    expect(bundle).toContain("# forkOS Source Diagnostics");
    expect(bundle).toContain(`Generated: ${GENERATED}`);
    expect(bundle).toContain("Scope: opportunity");
    expect(bundle).toContain("Source count: 48");
    expect(bundle).toContain("Problems: 1");
    // Kanonik kaynak kimliği (etiket değil) — ajan adapter'ı bununla bulur.
    expect(bundle).toContain("Source: forkjob_core:linkedin");
    expect(bundle).toContain("Label: LinkedIn Guest");
    expect(bundle).toContain("Class: Yavaş / isteğe bağlı");
    expect(bundle).toContain("Kind: İş ilanı");
    expect(bundle).toContain("Status: error");
    expect(bundle).toContain("Error kind: http_429");
    expect(bundle).toContain("Error kind label: 429");
    expect(bundle).toContain("Circuit open: true");
    expect(bundle).toContain("Consecutive failures: 5");
    expect(bundle).toContain("Consecutive empty: 0");
    expect(bundle).toContain("Last success: 2026-09-22T06:15:00.000Z");
    expect(bundle).toContain("Parser version: 3");
    expect(bundle).toContain("429 Too Many Requests");
  });

  it("eksik alanları uydurmaz, 'unknown/never' der", () => {
    const bundle = formatSourceDiagnostics({
      generated_at: GENERATED,
      scope: "media",
      source_count: null,
      problems: [{ source: "media:tmdb", label: "TMDB" }],
    });
    expect(bundle).toContain("Source count: unknown");
    expect(bundle).toContain("Status: unknown");
    expect(bundle).toContain("Circuit open: false");
    expect(bundle).toContain("Last run: never");
    expect(bundle).toContain("Last success: never");
    expect(bundle).toContain("Parser version: unknown");
    expect(bundle).toContain("(no sanitized error text reported)");
  });

  it("sorun yoksa bunu açıkça söyler (boş paket üretmez)", () => {
    const bundle = formatSourceDiagnostics({
      generated_at: GENERATED,
      scope: "opportunity",
      source_count: 42,
      problems: [],
    });
    expect(bundle).toContain("Problems: 0");
    expect(bundle).toContain("No reported source problems in the current diagnostic snapshot.");
  });

  it("bilinmeyen bölümleri atlamaz", () => {
    const bundle = formatSourceDiagnostics({
      generated_at: GENERATED,
      scope: "opportunity",
      source_count: null,
      problems: [],
      unknown: ["coverage"],
    });
    expect(bundle).toContain("Unknown sections: coverage");
  });

  it("sır görünümlü alanlar pakete girmez", () => {
    const bundle = formatSourceDiagnostics({
      generated_at: GENERATED,
      scope: "opportunity",
      source_count: 1,
      problems: [{ ...PROBLEM, last_error: "403 Forbidden" }],
    });
    for (const forbidden of ["token", "Bearer ", "api_key", "password", ".env", "postgresql://", "/Users/"]) {
      expect(bundle).not.toContain(forbidden);
    }
  });
});

describe("formatSystemDiagnostics", () => {
  it("yalnız verisi olan bölümleri yazar, bilinmeyeni dürüstçe listeler", () => {
    const input: SystemDiagnosticsInput = {
      generated_at: GENERATED,
      route: "/health",
      runtime: { api: "reachable", worker: "kapalı", uptime: "3 gün", cpu: "%12", memory: "%38", disk: "%74" },
      sources: { total: 42, healthy: 40, attention: 2, problems: [PROBLEM] },
      brain: { mcp: "hazır", tool_surface: "H0 -> H7", vault: "hazır", h4: "kapalı", h6: "kapalı", h7: "1 karar" },
      unknown: ["rss", "backup"],
    };
    const bundle = formatSystemDiagnostics(input);

    expect(bundle).toContain("# forkOS System Diagnostics");
    expect(bundle).toContain("Route: /health");
    expect(bundle).toContain("## Runtime");
    expect(bundle).toContain("Worker: kapalı");
    expect(bundle).toContain("## Sources");
    expect(bundle).toContain("Attention: 2");
    expect(bundle).toContain("- forkjob_core:linkedin (LinkedIn Guest)");
    expect(bundle).toContain("error_kind=http_429");
    expect(bundle).toContain("circuit_open=true");
    expect(bundle).toContain("## Brain Interface");
    expect(bundle).toContain("MCP: hazır");
    // Verisi olmayan bölüm yazılmaz...
    expect(bundle).not.toContain("## RSS");
    expect(bundle).not.toContain("## Backup");
    // ...ama gözlem boşluğu SAKLANMAZ.
    expect(bundle).toContain("## Unknown / Failed Diagnostics");
    expect(bundle).toContain("- rss: unknown — request failed");
    expect(bundle).toContain("- backup: unknown — request failed");
    // Sağlık iddiası yok, skor yok.
    expect(bundle).not.toMatch(/%\s*sağlık/i);
    expect(bundle).not.toContain("Hermes bağlı");
  });

  it("hiçbir bölüm yoksa bile kimlik ve bilinmeyen listesi kalır", () => {
    const bundle = formatSystemDiagnostics({
      generated_at: GENERATED,
      route: "/health",
      unknown: ["runtime", "sources", "rss", "backup", "brain"],
    });
    expect(bundle).toContain("# forkOS System Diagnostics");
    expect(bundle).toContain("- sources: unknown — request failed");
    expect(bundle).not.toContain("## Runtime");
  });

  it("hata metinlerini tek satıra indirir (liste görünümünü bozmaz)", () => {
    const bundle = formatSystemDiagnostics({
      generated_at: GENERATED,
      route: "/sources",
      sources: {
        total: 1,
        healthy: 0,
        attention: 1,
        problems: [{ ...PROBLEM, last_error: "satır bir\nsatır iki" }],
      },
      unknown: [],
    });
    expect(bundle).toContain("error: satır bir satır iki");
  });
});
