import { useCallback } from "react";
import { navigate } from "@/app/router";
import { Modal, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { MediaItem } from "@/core/types";
import { MediaSearchComposer } from "./MediaSearchComposer";

/**
 * Katalog arama diyalogu. Kapsam sekmeleri, debounce'lu saglayici aramasi ve
 * satir ici ekleme panosu `MediaSearchComposer` govdesinde yasar; burada
 * yalnizca modal katmani, odak yonetimi ve ekleme geri bildirimi var.
 *
 * `initialKind` acan yuzeyin aktif tur filtresidir (orn. MediaPage'in tur
 * filtresi) ve ilgili kapsam sekmesine cevrilir.
 */
export function MediaSearchDialog({
  open,
  onClose,
  initialKind,
}: {
  open: boolean;
  onClose: () => void;
  initialKind?: string;
}) {
  const online = useOnline();
  const toast = useToast();

  const handleAdded = useCallback(
    (item: MediaItem) => {
      onClose();
      toast.push("Kütüphaneye eklendi", {
        tone: "ok",
        action: { label: "Aç", run: () => navigate(`/media/${encodeURIComponent(item.id)}`) },
      });
    },
    [onClose, toast],
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Katalogda ara"
      hint="Sağlayıcı kataloğunda ara, kütüphanene ekle"
      className="sm:max-w-2xl"
    >
      <MediaSearchComposer online={online} initialKind={initialKind} onAdded={handleAdded} />
    </Modal>
  );
}
