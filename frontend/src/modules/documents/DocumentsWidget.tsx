import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Empty, RowList, Section, relativeTime } from "@/core/ui";
import type { Document } from "@/core/types";

/** Son degisen belgeler. */
export function DocumentsWidget() {
  const { data = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });
  const recent = [...data]
    .filter((doc) => doc.drive_modified_at)
    .sort((a, b) => (b.drive_modified_at ?? "").localeCompare(a.drive_modified_at ?? ""))
    .slice(0, 5);
  return (
    <Section title="Son belgeler">
      {recent.length === 0 ? (
        <Empty>Yeni belge yok.</Empty>
      ) : (
        <RowList>
          {recent.map((doc) => (
            <div key={doc.id} className="py-2">
              <a
                href={`#/documents?focus=${doc.id}`}
                className="block truncate text-body text-primary hover:text-accent"
              >
                {doc.title}
              </a>
              <p className="text-meta text-muted">{relativeTime(doc.drive_modified_at ?? doc.synced_at)}</p>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
