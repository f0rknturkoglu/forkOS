/**
 * Tanılama paketleri — SAF biçimlendiriciler.
 *
 * Amaç: bir arıza anında kullanıcının tüm gerekli bağlamı TEK tıkla, sır
 * sızdırmadan, bir kodlama ajanına yapıştırabilmesi. Beş bileşen kendi kopya
 * metnini kurmaz; hepsi bu iki fonksiyonu çağırır.
 *
 * Kurallar:
 *  - Yan etki YOK, DOM/pano/ağ erişimi YOK: saf string üretimi (kolay test).
 *  - Zaman DAMGA olarak DIŞARIDAN verilir (`generated_at`); böylece testler
 *    uçucu bir "şimdi" değerine bağlı kalmaz.
 *  - Sır, jeton, mutlak dosya yolu, .env, DB bağlantı dizesi, kişisel not
 *    içeriği ASLA pakete girmez. Hata metinleri backend'de zaten maskelenir
 *    (`core/runs.py`); burada ham istek başlığı veya URL eklenmez.
 *  - Bilinmeyen bölüm ATLANMAZ: "unknown — istek başarısız" olarak yazılır.
 *    Ajanın gözlem boşluğunu bilmesi gerekir.
 *  - Paket VERİDİR, talimat değildir: sonuna uzun bir "şunu yap" metni eklenmez.
 */
import { errorKindLabel, sourceClassLabel, sourceKindLabel } from "./sourceStatus";

/** Bir kaynak sorununun tanılama satırı (hepsi backend alanlarından gelir). */
export interface SourceProblemDiagnostic {
  /** Kanonik kaynak kimliği (adapter kimliği) — etiket değil. */
  source: string;
  label: string;
  source_class?: string | null;
  kind?: string | null;
  status?: string | null;
  error_kind?: string | null;
  circuit_open?: boolean | null;
  consecutive_failures?: number | null;
  consecutive_empty?: number | null;
  last_run_at?: string | null;
  last_success_at?: string | null;
  last_new_content_at?: string | null;
  parser_version?: string | null;
  last_error?: string | null;
}

/** Kaynak tanılama paketi girdisi. */
export interface SourceDiagnosticsInput {
  generated_at: string;
  scope: string;
  source_count: number | null;
  problems: SourceProblemDiagnostic[];
  /** Verisi alınamayan bölümler (ör. "coverage", "catalog"). */
  unknown?: string[];
}

function line(label: string, value: string | number | null | undefined): string | null {
  if (value === null || value === undefined || value === "") return null;
  return `${label}: ${value}`;
}

function block(lines: (string | null)[]): string {
  return lines.filter((item): item is string => item !== null).join("\n");
}

/** Kaynak sorunları paketi (Markdown). Sorun yoksa bunu açıkça söyler. */
export function formatSourceDiagnostics(input: SourceDiagnosticsInput): string {
  const head = block([
    "# forkOS Source Diagnostics",
    "",
    line("Generated", input.generated_at),
    line("Scope", input.scope),
    line("Source count", input.source_count ?? "unknown"),
    line("Problems", input.problems.length),
    line("Unknown sections", input.unknown?.length ? input.unknown.join(", ") : null),
  ]);

  if (input.problems.length === 0) {
    return `${head}\n\nNo reported source problems in the current diagnostic snapshot.`;
  }

  const sections = input.problems.map((problem, index) => {
    const kind = errorKindLabel(problem.error_kind);
    return block([
      `## Problem ${index + 1}`,
      "",
      line("Source", problem.source),
      line("Label", problem.label),
      line("Class", sourceClassLabel(problem.source_class)),
      line("Kind", sourceKindLabel(problem.kind)),
      line("Status", problem.status ?? "unknown"),
      line("Error kind", problem.error_kind ?? "none"),
      line("Error kind label", kind),
      line("Circuit open", problem.circuit_open === true ? "true" : "false"),
      line("Consecutive failures", problem.consecutive_failures ?? 0),
      line("Consecutive empty", problem.consecutive_empty ?? 0),
      line("Last run", problem.last_run_at ?? "never"),
      line("Last success", problem.last_success_at ?? "never"),
      line("Last new content", problem.last_new_content_at ?? "never"),
      line("Parser version", problem.parser_version ?? "unknown"),
      "",
      "Error:",
      problem.last_error?.trim() ? problem.last_error.trim() : "(no sanitized error text reported)",
    ]);
  });

  return [head, ...sections].join("\n\n");
}

/** Sistem tanılama paketi bölümleri; veri yoksa `null` geçilir. */
export interface SystemDiagnosticsInput {
  generated_at: string;
  route: string;
  runtime?: {
    api: string;
    worker: string;
    uptime?: string | null;
    cpu?: string | null;
    memory?: string | null;
    disk?: string | null;
  } | null;
  sources?: {
    total: number;
    healthy: number;
    attention: number;
    problems: SourceProblemDiagnostic[];
  } | null;
  rss?: {
    total: number;
    active: number;
    failing: number;
    disabled: number;
    errors?: string[];
  } | null;
  backup?: {
    last_backup_at?: string | null;
    last_backup_size?: string | null;
    pending_changes?: number | null;
    drive_configured: boolean;
    last_drive_error?: string | null;
  } | null;
  brain?: {
    mcp: string;
    tool_surface?: string | null;
    vault: string;
    h4: string;
    h6: string;
    h7: string;
  } | null;
  /** Verisi alınamayan bölümler — ATLANMAZ, açıkça yazılır. */
  unknown: string[];
}

/**
 * Sistem tanılama paketi (Markdown). Yalnız verisi olan bölümler yazılır;
 * verisi alınamayan bölümler "Unknown / Failed Diagnostics" altında listelenir.
 */
export function formatSystemDiagnostics(input: SystemDiagnosticsInput): string {
  const parts: string[] = [
    block(["# forkOS System Diagnostics", "", line("Generated", input.generated_at), line("Route", input.route)]),
  ];

  if (input.runtime) {
    parts.push(
      block([
        "## Runtime",
        line("API", input.runtime.api),
        line("Worker", input.runtime.worker),
        line("Uptime", input.runtime.uptime),
        line("CPU", input.runtime.cpu),
        line("Memory", input.runtime.memory),
        line("Disk", input.runtime.disk),
      ]),
    );
  }

  if (input.sources) {
    const problemLines = input.sources.problems.map((problem) =>
      block([
        `- ${problem.source} (${problem.label})`,
        `  status=${problem.status ?? "unknown"} error_kind=${problem.error_kind ?? "none"} circuit_open=${
          problem.circuit_open === true ? "true" : "false"
        } consecutive_empty=${problem.consecutive_empty ?? 0} consecutive_failures=${
          problem.consecutive_failures ?? 0
        }`,
        `  last_success=${problem.last_success_at ?? "never"} last_run=${problem.last_run_at ?? "never"}`,
        problem.last_error?.trim() ? `  error: ${problem.last_error.trim().replace(/\s+/g, " ")}` : null,
      ]),
    );
    parts.push(
      block([
        "## Sources",
        line("Total", input.sources.total),
        line("Healthy", input.sources.healthy),
        line("Attention", input.sources.attention),
        "",
        problemLines.length > 0 ? "Problems:" : "Problems: none",
        ...problemLines,
      ]),
    );
  }

  if (input.rss) {
    parts.push(
      block([
        "## RSS",
        line("Feeds", input.rss.total),
        line("Active", input.rss.active),
        line("Failing", input.rss.failing),
        line("Disabled", input.rss.disabled),
        input.rss.errors?.length ? `Recent errors: ${input.rss.errors.join(" | ")}` : null,
      ]),
    );
  }

  if (input.backup) {
    parts.push(
      block([
        "## Backup",
        line("Last backup", input.backup.last_backup_at ?? "none"),
        line("Last backup size", input.backup.last_backup_size),
        line("Pending changes", input.backup.pending_changes),
        line("Drive configured", input.backup.drive_configured ? "yes" : "no"),
        line("Last Drive error", input.backup.last_drive_error),
      ]),
    );
  }

  if (input.brain) {
    parts.push(
      block([
        "## Brain Interface",
        line("MCP", input.brain.mcp),
        line("Tool surface", input.brain.tool_surface),
        line("Vault", input.brain.vault),
        line("H4", input.brain.h4),
        line("H6", input.brain.h6),
        line("H7", input.brain.h7),
      ]),
    );
  }

  parts.push(
    block([
      "## Unknown / Failed Diagnostics",
      input.unknown.length > 0
        ? input.unknown.map((item) => `- ${item}: unknown — request failed`).join("\n")
        : "- none",
    ]),
  );

  return parts.filter((part) => part.trim().length > 0).join("\n\n");
}
