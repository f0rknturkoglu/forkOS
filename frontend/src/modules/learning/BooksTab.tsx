import { Trash2 } from "lucide-react";
import type { Book } from "@/core/types";
import { Chip, IconButton, NumberInput, RowList, Section } from "@/core/ui";

type Props = {
  books: Book[];
  online: boolean;
  onPage: (id: string, current_page: number) => void;
  onRemove: (id: string) => void;
};

export function BooksTab({ books, online, onPage, onRemove }: Props) {
  return (
    <Section title="Kitaplar">
      <RowList>
        {books.map((b) => (
          <div key={b.id} className="group flex flex-wrap items-center gap-3 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-body text-primary">{b.title}</p>
              <p className="text-meta text-muted">{b.author ?? "Yazar yok"}</p>
            </div>
            <Chip>{b.status}</Chip>
            <NumberInput value={b.current_page} disabled={!online} onChange={(n) => onPage(b.id, n)} className="w-20" />
            <span className="text-meta text-muted">/ {b.total_pages ?? "?"} sayfa</span>
            <IconButton
              title="Sil"
              tone="danger"
              disabled={!online}
              className="opacity-0 transition group-hover:opacity-100"
              onClick={() => onRemove(b.id)}
            >
              <Trash2 size={14} />
            </IconButton>
          </div>
        ))}
      </RowList>
    </Section>
  );
}
