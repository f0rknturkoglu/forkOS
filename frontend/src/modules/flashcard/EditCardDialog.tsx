import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button, Checkbox, Field, Modal, Textarea, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { patchCard } from "./api";
import { refreshFlashcards } from "./invalidate";
import type { FlashcardCard } from "./types";

/**
 * Kart duzenleme modali: cok satirli on/arka yuz + askiya alma.
 *
 * Satir ici duzenleme listeyi bozuyordu (uzun kartlar satirlari sisiriyordu);
 * duzenleme tek yuzeye tasindi.
 */
export function EditCardDialog({ card, onClose }: { card: FlashcardCard | null; onClose: () => void }) {
  const online = useOnline();
  const toast = useToast();
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [suspended, setSuspended] = useState(false);

  useEffect(() => {
    if (!card) return;
    setFront(card.front);
    setBack(card.back);
    setSuspended(card.suspended);
  }, [card]);

  const save = useMutation({
    mutationFn: () => patchCard(card!.id, { front: front.trim(), back: back.trim(), suspended }),
    onSuccess: () => {
      refreshFlashcards();
      toast.push("Kart güncellendi.", { tone: "ok" });
      onClose();
    },
    onError: () => toast.push("Kart güncellenemedi.", { tone: "danger" }),
  });

  const valid = front.trim().length > 0 && back.trim().length > 0;

  return (
    <Modal
      open={card !== null}
      onClose={onClose}
      title="Kartı düzenle"
      hint={card ? `${card.reps} tekrar · ${card.lapses} kez unutuldu` : undefined}
      ariaLabel="Kartı düzenle"
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button onClick={onClose}>Vazgeç</Button>
          <Button
            variant="primary"
            disabled={!online || !valid || save.isPending}
            onClick={() => save.mutate()}
            ariaLabel="Kaydet"
          >
            Kaydet
          </Button>
        </div>
      }
    >
      <Field label="Ön yüz (soru)">
        <Textarea value={front} onChange={setFront} ariaLabel="Kart ön yüzü" className="h-24" />
      </Field>
      <div className="mt-3">
        <Field label="Arka yüz (cevap)">
          <Textarea value={back} onChange={setBack} ariaLabel="Kart arka yüzü" className="h-24" />
        </Field>
      </div>
      <div className="mt-3">
        <Checkbox checked={suspended} onChange={setSuspended} label="Askıya al (tekrar kuyruğunda çıkmasın)" />
      </div>
    </Modal>
  );
}
