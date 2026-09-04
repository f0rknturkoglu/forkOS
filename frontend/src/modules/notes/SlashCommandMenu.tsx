import type { LucideIcon } from "lucide-react";
import {
  CheckSquare,
  Code2,
  FileAudio,
  FilePlus2,
  Heading1,
  Highlighter,
  Image,
  List,
  Minus,
  Paperclip,
  Quote,
  Table2,
} from "lucide-react";
import { cx } from "@/core/ui";

export interface SlashCommand {
  id: string;
  label: string;
  hint: string;
  keywords: string;
  icon: LucideIcon;
  markdown?: string;
  action?: "image" | "audio" | "file" | "highlights" | "new-note";
  caretOffset?: number;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: "heading",
    label: "Başlık",
    hint: "Bölüm başlığı",
    keywords: "başlık heading h1",
    icon: Heading1,
    markdown: "## Başlık",
    caretOffset: -6,
  },
  {
    id: "todo",
    label: "Görev",
    hint: "İşaretlenebilir todo",
    keywords: "todo görev checklist",
    icon: CheckSquare,
    markdown: "- [ ] Yapılacak",
    caretOffset: -9,
  },
  {
    id: "list",
    label: "Madde listesi",
    hint: "Sırasız liste",
    keywords: "liste bullet",
    icon: List,
    markdown: "- Madde",
    caretOffset: -5,
  },
  {
    id: "table",
    label: "Tablo",
    hint: "Markdown tablosu",
    keywords: "table tablo grid",
    icon: Table2,
    markdown: "| Sütun 1 | Sütun 2 |\n| --- | --- |\n| Değer | Değer |",
    caretOffset: -31,
  },
  {
    id: "quote",
    label: "Alıntı",
    hint: "Alıntı bloğu",
    keywords: "quote alıntı",
    icon: Quote,
    markdown: "> Alıntı",
    caretOffset: -6,
  },
  {
    id: "highlight",
    label: "Vurgu",
    hint: "Yer imlerinden alıntı ekle",
    keywords: "highlight vurgu yer imi bookmark",
    icon: Highlighter,
    action: "highlights",
  },
  {
    id: "code",
    label: "Kod",
    hint: "Kod bloğu",
    keywords: "code kod",
    icon: Code2,
    markdown: "```\nKod\n```",
    caretOffset: -7,
  },
  {
    id: "divider",
    label: "Ayraç",
    hint: "Bölümleri ayır",
    keywords: "divider ayraç çizgi",
    icon: Minus,
    markdown: "---",
  },
  {
    id: "image",
    label: "Görsel",
    hint: "Fotoğraf veya ekran görüntüsü",
    keywords: "image görsel fotoğraf",
    icon: Image,
    action: "image",
  },
  {
    id: "audio",
    label: "Ses",
    hint: "Ses dosyası ekle",
    keywords: "audio ses kayıt",
    icon: FileAudio,
    action: "audio",
  },
  {
    id: "file",
    label: "Dosya",
    hint: "PDF, video veya belge",
    keywords: "file dosya pdf video belge",
    icon: Paperclip,
    action: "file",
  },
  {
    id: "new-note",
    label: "Yeni not",
    hint: "Yeni bir not aç",
    keywords: "note not yeni",
    icon: FilePlus2,
    action: "new-note",
  },
];

export function slashContext(value: string, caret: number): { start: number; query: string } | null {
  const before = value.slice(0, caret);
  const lineStart = before.lastIndexOf("\n") + 1;
  const fragment = before.slice(lineStart);
  const match = fragment.match(/^\s*\/([^\s/]*)$/);
  if (!match) return null;
  return { start: lineStart + fragment.indexOf("/"), query: match[1].toLocaleLowerCase("tr") };
}

export function SlashCommandMenu({ query, onChoose }: { query: string; onChoose: (command: SlashCommand) => void }) {
  const filtered = SLASH_COMMANDS.filter((command) =>
    `${command.label} ${command.keywords}`.toLocaleLowerCase("tr").includes(query),
  );
  return (
    <div
      role="menu"
      aria-label="Slash komutları"
      className="absolute left-5 top-4 z-popover w-72 overflow-hidden rounded-overlay border border-strong bg-surface shadow-overlay"
    >
      <div className="border-b border-subtle px-3 py-2">
        <p className="text-meta font-medium text-primary">Blok ekle</p>
        <p className="text-micro text-muted">Yazmaya devam ederek filtrele</p>
      </div>
      <div className="max-h-80 overflow-y-auto p-1.5">
        {filtered.length === 0 ? (
          <p className="px-2 py-3 text-meta text-muted">Eşleşen komut yok.</p>
        ) : (
          filtered.map((command, index) => {
            const Icon = command.icon;
            return (
              <button
                key={command.id}
                type="button"
                role="menuitem"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => onChoose(command)}
                className={cx(
                  "flex w-full items-center gap-2.5 rounded-control px-2 py-2 text-left transition hover:bg-surface-hover",
                  index === 0 && "bg-surface-selected",
                )}
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-subtle bg-surface-sunken text-icon">
                  <Icon size={15} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-meta font-medium text-primary">{command.label}</span>
                  <span className="block truncate text-micro text-muted">{command.hint}</span>
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
