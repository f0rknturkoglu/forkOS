import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { entityRoute } from "@/core/entityRegistry";
import { Button, Field, Input, Select } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";

type S = components["schemas"];
type Node = S["StudyTopicLegacyNode"];
function flatten(nodes: Node[], parent = ""): { id: string; title: string }[] {
  return nodes.flatMap((node) => {
    const title = parent ? `${parent} / ${node.title}` : node.title;
    return [{ id: node.id, title }, ...flatten(node.children ?? [], title)];
  });
}

export function BookmarkLearningAttach({ bookmarkId }: { bookmarkId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <Button size="sm" ariaExpanded={open} onClick={() => setOpen((value) => !value)}>
        Öğrenme konusuna ekle
      </Button>
      {open && <TopicPicker key={bookmarkId} bookmarkId={bookmarkId} onClose={() => setOpen(false)} />}
    </div>
  );
}

function TopicPicker({ bookmarkId, onClose }: { bookmarkId: string; onClose: () => void }) {
  const [area, setArea] = useState("");
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState("");
  const [resultTopic, setResultTopic] = useState("");
  const online = useOnline();
  const areas = useQuery({ queryKey: ["study-areas"], queryFn: () => api.get<S["StudyAreaOut"][]>("/study/areas") });
  const tree = useQuery({
    queryKey: ["study-topics", area],
    queryFn: () => api.get<Node[]>(`/study/topics${qs({ area_id: area })}`),
    enabled: Boolean(area),
  });
  const attach = useMutation({
    mutationFn: () =>
      api.post<S["ResourceOut"]>("/study/resources/attach-bookmark", { topic_id: topic, bookmark_id: bookmarkId }),
    onSuccess: (resource) => {
      invalidateAfter("learning.write", "link.write");
      setResultTopic(resource.topic_id);
    },
  });
  const nodes = flatten(Array.isArray(tree.data) ? tree.data : []).filter((node) =>
    node.title.toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR")),
  );
  return (
    <div
      className="mt-2 w-full rounded-card border border-subtle bg-surface p-3 stack-y-2"
      aria-label="Öğrenme konusu seçimi"
    >
      <p className="text-meta text-muted">
        Mevcut yer imi kaynak olarak bağlanır. Koleksiyonu değişmez; tekrar ekleme aynı kaynağı kullanır.
      </p>
      <Field label="Çalışma alanı">
        <Select
          ariaLabel="Çalışma alanı"
          value={area}
          onChange={(value) => {
            setArea(value);
            setTopic("");
          }}
        >
          <option value="">Alan seç</option>
          {(areas.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </Select>
      </Field>
      <Input
        ariaLabel="Öğrenme konusu ara"
        placeholder="Bu alanın konularında ara"
        value={search}
        onChange={setSearch}
      />
      <Field label="Mevcut konu">
        <Select ariaLabel="Mevcut öğrenme konusu" value={topic} onChange={setTopic} disabled={!area || tree.isFetching}>
          <option value="">Konu seç</option>
          {nodes.map((node) => (
            <option key={node.id} value={node.id}>
              {node.title}
            </option>
          ))}
        </Select>
      </Field>
      {area && !tree.isFetching && !tree.isError && nodes.length === 0 && (
        <p className="text-meta text-muted">Eşleşen konu yok.</p>
      )}
      {(areas.isError || tree.isError) && (
        <p role="alert" className="text-meta text-danger">
          Konu listesi alınamadı.{" "}
          <Button
            onClick={() => {
              void areas.refetch();
              if (area) void tree.refetch();
            }}
          >
            Yeniden dene
          </Button>
        </p>
      )}
      {attach.isError && (
        <p role="alert" className="text-meta text-danger">
          Kaynak bağlanamadı; seçimin korunuyor.
        </p>
      )}
      {resultTopic && (
        <p role="status" className="text-meta text-ok">
          Kaynak bağlandı.{" "}
          <a className="underline" href={`#${entityRoute("study_topic", resultTopic)}`}>
            Konuyu aç
          </a>
        </p>
      )}
      <div className="flex gap-2">
        <Button disabled={!online || !topic || attach.isPending} onClick={() => attach.mutate()}>
          {attach.isPending ? "Bağlanıyor…" : "Konuyu bağla"}
        </Button>
        <Button onClick={onClose}>Kapat</Button>
      </div>
    </div>
  );
}
