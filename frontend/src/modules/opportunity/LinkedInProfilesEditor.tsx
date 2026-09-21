import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Checkbox, Empty, IconButton, Input, NumberInput, Section, useToast } from "@/core/ui";

/** LinkedIn arama profili; alanlar backend `to_dict` çıktısıyla aynıdır. */
interface LinkedInProfile {
  term: string;
  location?: string;
  results_wanted?: number;
  /** UI'da düzenlenmez ama PUT tüm listeyi yazdığı için korunur. */
  hours_old?: number;
  fetch_description?: boolean;
  is_remote?: boolean;
}

/**
 * LinkedIn arama profilleri: ekle, düzenle, sil, kaydet.
 *
 * Kaydetme tüm listeyi `PUT /sources/jobhunter/linkedin-profiles` ile yazar;
 * backend satırları gitignored yerel YAML dosyasına (`linkedin-profiles.yaml.user`)
 * attığı için bu profiller repoya girmez. Aynı bileşen Jobhunter ayarlarında ve
 * Ayarlar → Kariyer profili sekmesinde kullanılır (tek kopya).
 */
export function LinkedInProfilesEditor({ online }: { online: boolean }) {
  const toast = useToast();
  const profilesQuery = useQuery({
    queryKey: ["jobhunter-linkedin"],
    queryFn: () => api.get<LinkedInProfile[]>("/sources/jobhunter/linkedin-profiles"),
  });

  const [editing, setEditing] = useState<LinkedInProfile[]>([]);
  useEffect(() => {
    if (profilesQuery.data) setEditing(profilesQuery.data);
  }, [profilesQuery.data]);

  const save = useMutation({
    mutationFn: () => api.put("/sources/jobhunter/linkedin-profiles", editing),
    onSuccess: () => {
      invalidateAfter("jobhunter.write");
      toast.push(`${editing.length} LinkedIn profili kaydedildi.`, { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`Profiller kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });

  function patch(index: number, next: Partial<LinkedInProfile>) {
    setEditing((prev) => prev.map((row, i) => (i === index ? { ...row, ...next } : row)));
  }

  return (
    <Section title="LinkedIn arama profilleri">
      <p className="mb-2 text-meta text-muted">
        Varsayılan profiller portallarla birleşir; seninkiler en sona eklenir ve senkron turlarında çalışır.
      </p>
      <div className="space-y-2">
        {editing.map((row, index) => (
          <div
            key={index}
            className="grid gap-1.5 rounded-control border border-subtle p-2 sm:grid-cols-[1fr_1fr_5rem_4rem_auto]"
          >
            <Input
              value={row.term}
              onChange={(term) => patch(index, { term })}
              placeholder="Arama terimi"
              className="w-full"
            />
            <Input
              value={row.location ?? ""}
              onChange={(location) => patch(index, { location })}
              placeholder="Konum (ops.)"
              className="w-full"
            />
            <NumberInput
              value={row.results_wanted ?? 50}
              onChange={(results_wanted) => patch(index, { results_wanted })}
              ariaLabel="Sonuç sayısı"
              className="w-full"
            />
            <Checkbox
              checked={Boolean(row.is_remote)}
              onChange={(is_remote) => patch(index, { is_remote })}
              label="Uzak"
              className="text-meta text-muted"
            />
            <IconButton
              title="Profili sil"
              tone="danger"
              onClick={() => setEditing((prev) => prev.filter((_, i) => i !== index))}
            >
              <Trash2 size={13} />
            </IconButton>
          </div>
        ))}
        {editing.length === 0 && <Empty>Henüz profil yok — ekle.</Empty>}
      </div>
      <div className="mt-3 flex items-center justify-between">
        <Button size="sm" onClick={() => setEditing((prev) => [...prev, { term: "" }])}>
          <Plus size={13} /> Profil ekle
        </Button>
        <Button
          variant="primary"
          size="sm"
          disabled={!online || editing.some((row) => !row.term.trim()) || save.isPending}
          onClick={() => save.mutate()}
        >
          <Check size={13} /> Kaydet
        </Button>
      </div>
      {!online && <p className="mt-2 text-meta text-warn">Çevrimdışısın: kaydetmek için bağlantı gerekir.</p>}
    </Section>
  );
}
