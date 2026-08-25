import type { Bookmark } from "@/core/types";
import { RowList, Section, Select } from "@/core/ui";

const queueKinds = ["watch", "read", "listen", "practice"] as const;
const queueKindLabels: Record<string, string> = {
  watch: "İzle",
  read: "Oku",
  listen: "Dinle",
  practice: "Uygula",
};

type Props = {
  queue: Bookmark[];
  online: boolean;
  onMove: (id: string, queue_kind: string) => void;
};

export function QueueTab({ queue, online, onMove }: Props) {
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
      {queueKinds.map((kind) => (
        <Section key={kind} title={queueKindLabels[kind]}>
          <RowList>
            {queue
              .filter((x) => (x.queue_kind ?? "read") === kind)
              .map((x) => (
                <article key={x.id} className="py-2">
                  <a href={x.url} target="_blank" rel="noreferrer" className="text-meta hover:text-accent">
                    {x.title}
                  </a>
                  <Select
                    value={x.queue_kind ?? "read"}
                    disabled={!online}
                    onChange={(v) => onMove(x.id, v)}
                    className="mt-2 w-full"
                  >
                    {queueKinds.map((k) => (
                      <option key={k} value={k}>
                        {queueKindLabels[k]}
                      </option>
                    ))}
                  </Select>
                </article>
              ))}
          </RowList>
        </Section>
      ))}
    </div>
  );
}
