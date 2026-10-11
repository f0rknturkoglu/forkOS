import { Code2 } from "lucide-react";
import { cx } from "./ui";

const LOGOS: Record<string, string> = {
  lean: "lean",
  typescript: "typescript",
  javascript: "javascript",
  python: "python",
  swift: "swift",
  rust: "rust",
  go: "go",
  java: "java",
  kotlin: "kotlin",
  c: "c",
  cpp: "cplusplus",
  csharp: "csharp",
  ruby: "ruby",
  php: "php",
  dart: "dart",
  html: "html5",
  css: "css3",
  shell: "bash",
  bash: "bash",
};

/** Dil kimliği küçük, yerel SVG'dedir; etiket tüm temalarda nötr kalır. */
export function TechnologyBadge({ language }: { language: string }) {
  const key = language
    .toLowerCase()
    .replace(/\+/g, "p")
    .replace(/#/g, "sharp")
    .replace(/[^a-z0-9]/g, "");
  const logo = LOGOS[key];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-control border border-subtle px-1.5 py-0.5 text-micro leading-4 text-secondary">
      {logo ? (
        <img
          src={`/technology/${logo}.${logo === "lean" ? "png" : "svg"}`}
          alt=""
          aria-hidden="true"
          className={cx("h-3.5 w-3.5 shrink-0", (logo === "rust" || logo === "bash") && "technology-logo-monochrome")}
        />
      ) : (
        <Code2 size={14} aria-hidden="true" />
      )}
      {language}
    </span>
  );
}
