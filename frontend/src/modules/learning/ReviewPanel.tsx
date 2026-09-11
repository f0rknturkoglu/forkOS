/**
 * Konunun tekrar (SRS) paneli.
 *
 * Dereceler backend `GRADES` ile ayni kumede ve sirada: forgot, hard, medium,
 * easy, very_easy. Aralik hesabi frontend'de TEKRARLANMAZ -- yeni aralik
 * backend yanitindan okunur ve kullaniciya dogrudan gosterilir.
 *
 * Kart uretimi YOK: deste icindeki kartlari kullanici acikca yazar.
 */
import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Brain, ExternalLink, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { linkEntities } from "@/core/links";
import {
  Button,
  Chip,
  Empty,
  Field,
  IconButton,
  Input,
  Modal,
  SectionHeader,
  SkeletonRows,
  Textarea,
  cx,
  relativeTime,
  useToast,
} from "@/core/ui";
import { addCard, createDeck, deleteDeck, listDecks } from "@/modules/flashcard/api";
import type { FlashcardDeck } from "@/modules/flashcard/types";
import { formatTrDate } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";

type ReviewBlockOut = components["schemas"]["ReviewBlockOut"];

/** Unuttum -> Çok kolay. Her derecenin kullaniciya gorunen sonucu. */
export const REVIEW_GRADES = [
  { id: "forgot", label: "Unuttum", hint: "Aralık sıfırlanır, bugün tekrar" },
  { id: "hard", label: "Zor", hint: "Aralık az artar" },
  { id: "medium", label: "Orta", hint: "Aralık iki katına çıkar" },
  { id: "easy", label: "Kolay", hint: "Aralık 2,5 katına çıkar" },
  { id: "very_easy", label: "Çok kolay", hint: "Aralık üç katına çıkar" },
] as const;

type ReviewGrade = (typeof REVIEW_GRADES)[number]["id"];

/** Gecikme/erteleme durumu: rozet metni + tonu. */
export function dueLabel(
  review: { due: boolean; next_review_at?: string | null },
  now: number = Date.now(),
): { text: string; tone: "ok" | "warn" | "danger" | "neutral" } {
  if (!review.next_review_at) return { text: "Tekrar planlanmadı", tone: "neutral" };
  const diff = new Date(review.next_review_at).getTime() - now;
  if (diff <= 0) {
    const late = Math.floor(-diff / 86_400_000);
    if (late >= 1) return { text: `${late} gün gecikti`, tone: "danger" };
    return { text: "Bugün tekrar", tone: "warn" };
  }
  const days = Math.ceil(diff / 86_400_000);
  if (days <= 1) return { text: "Yarın tekrar", tone: "ok" };
  return { text: `${days} gün sonra`, tone: "ok" };
}

export function ReviewPanel({
  topicId,
  review,
  confidence,
  lastStudiedAt,
}: {
  topicId: string;
  review: ReviewBlockOut;
  confidence: number | null;
  lastStudiedAt: string | null;
}) {
  const [grade, setGrade] = useState<ReviewGrade | null>(null);
  const [result, setResult] = useState<ReviewBlockOut | null>(null);
  const [cardDeck, setCardDeck] = useState<FlashcardDeck | null>(null);
  const [cardFront, setCardFront] = useState("");
  const [cardBack, setCardBack] = useState("");
  const [newDeckOpen, setNewDeckOpen] = useState(false);
  const [deckTitle, setDeckTitle] = useState("");
  const gradeRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const online = useOnline();
  const toast = useToast();

  const { data: decks = [], isLoading: decksLoading } = useQuery({
    queryKey: ["flashcard", "decks", "linked", topicId],
    queryFn: () => listDecks(topicId),
  });

  const reviewMutation = useMutation({
    mutationFn: (value: ReviewGrade) => api.post<ReviewBlockOut>(`/study/topics/${topicId}/review`, { grade: value }),
    onSuccess: (fresh) => {
      setResult(fresh);
      setGrade(null);
      invalidateAfter("study.write");
    },
  });

  const addCardMutation = useMutation({
    mutationFn: () => addCard(cardDeck?.id ?? "", cardFront.trim(), cardBack.trim()),
    onSuccess: () => {
      setCardFront("");
      setCardBack("");
      setCardDeck(null);
      invalidateAfter("flashcard.write");
      toast.push("Kart desteye eklendi.", { tone: "ok" });
    },
  });

  const newDeckMutation = useMutation({
    mutationFn: async () => {
      const deck = await createDeck(deckTitle.trim());
      // Deste -> konu bagi olmadan panelde gorunmez (linked_to bu bagi okur).
      await linkEntities(deck.id, topicId, "studies");
      return deck;
    },
    onSuccess: () => {
      setDeckTitle("");
      setNewDeckOpen(false);
      invalidateAfter("flashcard.write");
    },
  });

  const removeDeck = useMutation({
    mutationFn: (deckId: string) => deleteDeck(deckId),
    onSuccess: () => invalidateAfter("flashcard.write"),
  });

  const confirmRemoveDeck = async (deck: FlashcardDeck) => {
    const ok = await confirmDialog({
      title: `"${deck.title}" destesi silinsin mi?`,
      body: `${deck.card_count} kart ve tekrar geçmişi birlikte silinir.`,
      confirmLabel: "Desteyi sil",
      tone: "danger",
    });
    if (ok) removeDeck.mutate(deck.id);
  };

  const current = result ?? review;
  const status = dueLabel(current);
  const tone = status.tone === "danger" ? "text-danger" : status.tone === "warn" ? "text-warn" : "text-muted";

  // Radyo grubunda ok tuslari: secimi degistirir ve odagi tasir. Hicbir derece
  // secili degilken ilk ok ilk dereceyi secer (klavye kullanicisi bos kalmasin).
  const moveGrade = (base: number, step: number) => {
    const next = (base + step + REVIEW_GRADES.length) % REVIEW_GRADES.length;
    setGrade(REVIEW_GRADES[next].id);
    gradeRefs.current[next]?.focus();
  };

  const facts: { label: string; value: string }[] = [
    { label: "Son çalışma", value: lastStudiedAt ? relativeTime(lastStudiedAt) : "—" },
    { label: "Son tekrar", value: current.last_reviewed_at ? relativeTime(current.last_reviewed_at) : "—" },
    { label: "Sonraki tekrar", value: current.next_review_at ? formatTrDate(current.next_review_at) : "—" },
    { label: "Tekrar sayısı", value: String(current.review_count) },
    { label: "Güven", value: confidence ? `${confidence}/5` : "—" },
    {
      label: "Ustalık",
      value: current.mastery !== null && current.mastery !== undefined ? `%${current.mastery}` : "—",
    },
  ];

  return (
    <div className="space-y-5">
      <SectionHeader label="Tekrar" hint={<span className={tone}>{status.text}</span>} />

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-body sm:grid-cols-3">
        {facts.map((fact) => (
          <div key={fact.label} className="min-w-0">
            <dt className="text-meta text-muted">{fact.label}</dt>
            <dd className="truncate font-medium text-primary">{fact.value}</dd>
          </div>
        ))}
      </dl>

      <div className="rounded-card border border-subtle bg-surface p-3.5">
        <p className="mb-2 flex items-center gap-1.5 text-meta font-medium text-secondary">
          <Brain size={13} /> Tekrarı tamamla — ne kadar hatırladın?
        </p>
        <div
          role="radiogroup"
          aria-label="Tekrar derecesi"
          className="flex flex-wrap gap-1.5"
          onKeyDown={(event) => {
            const forward = event.key === "ArrowRight" || event.key === "ArrowDown";
            const backward = event.key === "ArrowLeft" || event.key === "ArrowUp";
            if (!forward && !backward) return;
            event.preventDefault();
            const index = REVIEW_GRADES.findIndex((item) => item.id === grade);
            moveGrade(index < 0 ? -1 : index, forward ? 1 : -1);
          }}
        >
          {REVIEW_GRADES.map((item, index) => {
            const active = item.id === grade;
            return (
              <button
                key={item.id}
                ref={(node) => {
                  gradeRefs.current[index] = node;
                }}
                type="button"
                role="radio"
                aria-checked={active}
                aria-label={`${item.label} — ${item.hint}`}
                title={item.hint}
                tabIndex={active || (grade === null && index === 0) ? 0 : -1}
                disabled={!online || reviewMutation.isPending}
                onClick={() => setGrade(item.id)}
                className={cx(
                  "inline-flex h-8 items-center rounded-control border px-3 text-meta font-medium transition",
                  active
                    ? "border-accent-border bg-accent-surface text-accent"
                    : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
                  (!online || reviewMutation.isPending) && "cursor-not-allowed opacity-40",
                )}
              >
                {item.label}
              </button>
            );
          })}
        </div>
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-subtle pt-3">
          <p className="text-meta text-muted">
            {grade ? (REVIEW_GRADES.find((item) => item.id === grade)?.hint ?? "") : "Bir derece seç, sonra kaydet."}
          </p>
          <Button
            variant="primary"
            size="sm"
            disabled={!online || !grade || reviewMutation.isPending}
            onClick={() => grade && reviewMutation.mutate(grade)}
          >
            Tekrarı tamamla
          </Button>
        </div>
        {result?.next_review_at && (
          <p role="status" className="mt-2 text-meta font-medium text-ok">
            Sonraki tekrar: {formatTrDate(result.next_review_at)} ({result.interval_days} gün)
          </p>
        )}
      </div>

      <div>
        <SectionHeader
          label="Flashcard desteleri"
          hint={`${decks.length} deste`}
          action={
            <Button size="sm" disabled={!online} onClick={() => setNewDeckOpen(true)}>
              <Plus size={13} /> Yeni deste
            </Button>
          }
        />
        {decksLoading ? (
          <SkeletonRows rows={2} />
        ) : decks.length === 0 ? (
          <Empty>Bu konuya bağlı deste yok. "Yeni deste" ile oluşturup konuya bağlayabilirsin.</Empty>
        ) : (
          <ul className="divide-y divide-subtle">
            {decks.map((deck) => (
              <li key={deck.id} className="flex items-center gap-2 py-2">
                <span className="min-w-0 flex-1 truncate text-body text-primary">{deck.title}</span>
                <Chip size="xs">{deck.card_count} kart</Chip>
                {deck.due_count > 0 && (
                  <Chip size="xs" tone="warn">
                    {deck.due_count} vadesi gelen
                  </Chip>
                )}
                <Button
                  size="sm"
                  onClick={() => {
                    setCardFront("");
                    setCardBack("");
                    setCardDeck(deck);
                  }}
                >
                  Kart ekle
                </Button>
                <a
                  href={`#/flashcard?deck=${deck.id}`}
                  className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-control border border-strong bg-surface px-3 text-meta font-medium text-primary transition hover:bg-surface-hover"
                >
                  <ExternalLink size={13} /> Deste aç
                </a>
                <IconButton
                  title="Deste sil"
                  tone="danger"
                  disabled={!online || removeDeck.isPending}
                  onClick={() => confirmRemoveDeck(deck)}
                >
                  <Trash2 size={13} />
                </IconButton>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Modal
        open={cardDeck !== null}
        onClose={() => setCardDeck(null)}
        title={`Kart ekle — ${cardDeck?.title ?? ""}`}
        hint="Kartı sen yazarsın; otomatik üretim yok."
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCardDeck(null)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !cardFront.trim() || !cardBack.trim() || addCardMutation.isPending}
              onClick={() => addCardMutation.mutate()}
            >
              Kartı ekle
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <Field label="Ön yüz">
            <Textarea value={cardFront} onChange={setCardFront} rows={2} className="w-full" />
          </Field>
          <Field label="Arka yüz">
            <Textarea value={cardBack} onChange={setCardBack} rows={2} className="w-full" />
          </Field>
        </div>
      </Modal>

      <Modal
        open={newDeckOpen}
        onClose={() => setNewDeckOpen(false)}
        title="Yeni deste"
        hint="Deste oluşturulur ve bu konuya bağlanır (studies)."
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setNewDeckOpen(false)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !deckTitle.trim() || newDeckMutation.isPending}
              onClick={() => newDeckMutation.mutate()}
            >
              Oluştur
            </Button>
          </div>
        }
      >
        <Field label="Deste adı">
          <Input value={deckTitle} onChange={setDeckTitle} placeholder=".gitignore komutları" className="w-full" />
        </Field>
      </Modal>
    </div>
  );
}
