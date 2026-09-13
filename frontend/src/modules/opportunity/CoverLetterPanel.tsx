import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Sparkles } from "lucide-react";
import { api } from "@/core/api";
import { Button, Chip, Empty, Field, Metric, MetricStrip, Section, Select, Textarea, useToast } from "@/core/ui";
import type { CareerStory, CoverLetter, CoverLetterReview } from "@/core/types";

/** Kaydedilmiş ön yazı: toplu uçtan gelen düz kayıt (ilan nesnesi taşımaz). */
type SavedLetter = CoverLetter;

export function CoverLetterPanel() {
  const toast = useToast();
  const [text, setText] = useState("");
  const [selectedLetterId, setSelectedLetterId] = useState("");
  const [review, setReview] = useState<CoverLetterReview | null>(null);
  const { data: letters = [] } = useQuery({
    queryKey: ["career-cover-letters"],
    // Kayıt başına istek YOK: kaydedilmiş ön yazılar tek uçtan gelir.
    queryFn: async (): Promise<SavedLetter[]> => {
      return api.get<CoverLetter[]>("/career/cover-letters");
    },
  });
  const { data: stories = [] } = useQuery({
    queryKey: ["career-stories"],
    queryFn: () => api.get<CareerStory[]>("/career/stories"),
  });

  const evaluate = useMutation({
    mutationFn: (value: string) => api.post<CoverLetterReview>("/career/cover-letter-review", { text: value }),
    onSuccess: setReview,
    onError: (error: Error) => toast.push(`Ön yazı değerlendirilemedi: ${error.message}`, { tone: "danger" }),
  });

  const tooShort = text.trim().length < 20;
  const scoreTone: "ok" | "warn" | "danger" = review
    ? review.score >= 70
      ? "ok"
      : review.score >= 45
        ? "warn"
        : "danger"
    : "warn";

  return (
    <Section title="Ön yazı denetimi" hint="Değerlendirme tamamen yerel çalışır">
      <div className="space-y-3">
        <Field label="Kayıtlı ön yazıdan yükle">
          <Select
            value={selectedLetterId}
            onChange={(value) => {
              setSelectedLetterId(value);
              const found = letters.find((row) => row.opportunity_id === value);
              if (found) {
                setText(found.cover_letter);
                setReview(null);
              }
            }}
            ariaLabel="Kayıtlı ön yazı seç"
            className="w-full"
          >
            <option value="">Bir başvurunun ön yazısını seç…</option>
            {letters.map((letter) => (
              <option key={letter.opportunity_id} value={letter.opportunity_id}>
                {letter.title}
                {letter.organization ? ` · ${letter.organization}` : ""}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Ön yazı metni" hint="Yapıştır ya da yukarıdan seç.">
          <Textarea
            value={text}
            onChange={(value) => {
              setText(value);
              setReview(null);
            }}
            rows={10}
            placeholder="Sayın işe alım ekibi…"
          />
        </Field>
        <div className="flex items-center gap-2">
          <Button variant="primary" disabled={tooShort || evaluate.isPending} onClick={() => evaluate.mutate(text)}>
            <Sparkles size={14} /> {evaluate.isPending ? "Değerlendiriliyor…" : "Ön yazıyı değerlendir"}
          </Button>
          {tooShort && <span className="text-meta text-muted">En az 20 karakter gerekir.</span>}
        </div>

        {review && (
          <div className="space-y-3 rounded-card border border-subtle bg-surface-sunken p-4">
            <MetricStrip>
              <Metric label="Puan" value={`${review.score} / 100`} />
              <Metric label="Kalıp ifade" value={review.generic_phrases.length} />
              <Metric label="Eşleşen hikâye" value={review.matched_story_ids.length} />
              <Metric label="Düzeltme" value={review.suggestions.length} />
            </MetricStrip>
            <div className={scoreTone === "ok" ? "text-ok" : scoreTone === "warn" ? "text-warn" : "text-danger"}>
              <span className="text-meta font-medium">
                {scoreTone === "ok" ? "Güçlü taslak" : scoreTone === "warn" ? "Geliştirilebilir" : "Zayıf taslak"}
              </span>
            </div>

            <div>
              <span className="text-meta font-medium text-secondary">Kalıp ifadeler</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {review.generic_phrases.length === 0 ? (
                  <span className="text-meta text-muted">Kalıp ifade yakalanmadı.</span>
                ) : (
                  review.generic_phrases.map((phrase) => (
                    <Chip key={phrase} tone="warn">
                      {phrase}
                    </Chip>
                  ))
                )}
              </div>
            </div>

            <div>
              <span className="text-meta font-medium text-secondary">Eşleşen hikâyeler</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {review.matched_story_ids.length === 0 ? (
                  <span className="text-meta text-muted">
                    Hikâye bankasından somut bir bağ kurulamadı; bir STAR+R hikâyesi ekle.
                  </span>
                ) : (
                  review.matched_story_ids.map((id) => {
                    const story = stories.find((item) => item.id === id);
                    return (
                      <Chip key={id} tone="accent" icon={<FileText size={11} />}>
                        {story?.title ?? id.slice(0, 8)}
                      </Chip>
                    );
                  })
                )}
              </div>
            </div>

            {review.flags.length > 0 && (
              <div>
                <span className="text-meta font-medium text-secondary">Bulgular</span>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-meta text-secondary">
                  {review.flags.map((flag) => (
                    <li key={flag}>{flag}</li>
                  ))}
                </ul>
              </div>
            )}

            {review.suggestions.length > 0 && (
              <div>
                <span className="text-meta font-medium text-secondary">Somut düzeltmeler</span>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-meta text-secondary">
                  {review.suggestions.map((suggestion) => (
                    <li key={suggestion}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {!review && letters.length === 0 && (
          <Empty title="Kayıtlı ön yazı yok">
            Metni yapıştırıp değerlendirebilirsin; başvuru kaydına ön yazı eklediğinde buradan da seçilebilir.
          </Empty>
        )}
      </div>
    </Section>
  );
}
