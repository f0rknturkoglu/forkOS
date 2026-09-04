import { type ComponentProps, useEffect, useMemo, useRef, useState } from "react";
import { convertToExcalidrawElements, Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";
import type { BinaryFileData, DataURL, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import type { FileId } from "@excalidraw/excalidraw/element/types";
import { Button, Chip, type Theme } from "@/core/ui";
import type { NoteAttachment, NoteCanvasState } from "@/core/types";
import { Link2, Paperclip } from "lucide-react";
import { attachmentSkeletons } from "./canvasAttachments";

type NoteCanvasProps = {
  initialState: NoteCanvasState;
  noteId: string;
  noteTitle: string;
  attachments: NoteAttachment[];
  readOnly: boolean;
  theme: Theme;
  onSave: (state: NoteCanvasState) => void;
};

type OnCanvasChange = NonNullable<ComponentProps<typeof Excalidraw>["onChange"]>;
type CanvasElements = Parameters<OnCanvasChange>[0];
type CanvasAppState = Parameters<OnCanvasChange>[1];
type CanvasFiles = Parameters<OnCanvasChange>[2];

function sceneState(
  elements: CanvasElements,
  appState: CanvasAppState,
  files: CanvasFiles,
  linkedFileIds: Set<string>,
): NoteCanvasState {
  return {
    type: "excalidraw",
    version: 2,
    elements: [...elements],
    appState: {
      viewBackgroundColor: appState.viewBackgroundColor,
      scrollX: appState.scrollX,
      scrollY: appState.scrollY,
      zoom: appState.zoom,
      gridSize: appState.gridSize,
    },
    // Not ekleri kendi API kaydında kalır; tuval yalnızca attachment id'sini
    // saklar. Böylece aynı görsel base64 olarak iki kez DB'ye yazılmaz.
    files: Object.fromEntries(Object.entries(files).filter(([id]) => !linkedFileIds.has(id))),
  };
}

function blobDataUrl(blob: Blob): Promise<DataURL> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("Dosya okunamadı"));
    reader.onload = () => resolve(reader.result as DataURL);
    reader.readAsDataURL(blob);
  });
}

async function attachmentFile(attachment: NoteAttachment): Promise<BinaryFileData> {
  if (!/^\/api\/notes\/[0-9a-f-]+\/attachments\/[0-9a-f-]+$/i.test(attachment.url)) {
    throw new Error("Yalnızca yerel not ekleri tuvale alınabilir");
  }
  const response = await fetch(attachment.url);
  if (!response.ok) throw new Error(`${attachment.name} yüklenemedi`);
  return {
    id: attachment.id as FileId,
    dataURL: await blobDataUrl(await response.blob()),
    mimeType: attachment.mime as BinaryFileData["mimeType"],
    created: Date.now(),
  };
}

type CanvasSkeleton = NonNullable<Parameters<typeof convertToExcalidrawElements>[0]>[number];

/** Excalidraw sahnesini forkOS notuna gecikmeli ve yerel olarak kaydeder. */
export default function NoteCanvas({
  initialState,
  noteId,
  noteTitle,
  attachments,
  readOnly,
  theme,
  onSave,
}: NoteCanvasProps) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pending = useRef<NoteCanvasState | null>(null);
  const lastSaved = useRef(JSON.stringify(initialState));
  const onSaveRef = useRef(onSave);
  const canvasApi = useRef<ExcalidrawImperativeAPI | null>(null);
  const [placing, setPlacing] = useState(false);
  const [canvasMessage, setCanvasMessage] = useState("");
  onSaveRef.current = onSave;

  const linkedFileIds = useMemo(
    () => new Set(attachments.filter((item) => item.mime.startsWith("image/")).map((item) => item.id)),
    [attachments],
  );

  const initialData = useMemo(
    () => ({
      elements: (initialState.elements ?? []) as unknown as CanvasElements,
      appState: initialState.appState ?? {},
      files: (initialState.files ?? {}) as CanvasFiles,
    }),
    [initialState],
  );

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      if (pending.current) onSaveRef.current(pending.current);
    },
    [],
  );

  async function hydrateLinkedImages(api: ExcalidrawImperativeAPI) {
    const linkedIds = new Set(
      api
        .getSceneElements()
        .filter((element) => element.type === "image")
        .map((element) => String(element.customData?.noteAttachmentId ?? ""))
        .filter(Boolean),
    );
    const missing = attachments.filter(
      (attachment) =>
        attachment.mime.startsWith("image/") && linkedIds.has(attachment.id) && !api.getFiles()[attachment.id],
    );
    if (!missing.length) return;
    const files = await Promise.all(missing.map(attachmentFile));
    api.addFiles(files);
  }

  async function placeAttachments() {
    const api = canvasApi.current;
    if (!api || readOnly || !attachments.length) return;
    setPlacing(true);
    setCanvasMessage("");
    try {
      const current = api.getSceneElements();
      const placed = new Set(
        current.map((element) => String(element.customData?.noteAttachmentId ?? "")).filter(Boolean),
      );
      const pendingAttachments = attachments.filter((attachment) => !placed.has(attachment.id));
      if (!pendingAttachments.length) {
        setCanvasMessage("Bütün ekler zaten tuvalde.");
        return;
      }

      const files = await Promise.all(
        pendingAttachments.filter((attachment) => attachment.mime.startsWith("image/")).map(attachmentFile),
      );
      if (files.length) api.addFiles(files);

      const skeletons = attachmentSkeletons(pendingAttachments, placed) as CanvasSkeleton[];
      const created = convertToExcalidrawElements(skeletons, { regenerateIds: true });
      api.updateScene({ elements: [...current, ...created] });
      api.scrollToContent(created, { fitToContent: true, animate: true });
      setCanvasMessage(`${pendingAttachments.length} ek tuvale yerleştirildi.`);
    } catch (error) {
      setCanvasMessage(error instanceof Error ? error.message : "Ekler tuvale yerleştirilemedi.");
    } finally {
      setPlacing(false);
    }
  }

  function placeNoteCard() {
    const api = canvasApi.current;
    if (!api || readOnly) return;
    const current = api.getSceneElements();
    const alreadyPlaced = current.some((element) => element.customData?.noteEntityId === noteId);
    if (alreadyPlaced) {
      setCanvasMessage("Not kartı zaten tuvalde.");
      return;
    }
    const created = convertToExcalidrawElements(
      [
        {
          type: "rectangle",
          x: 80,
          y: 80,
          width: 360,
          height: 120,
          link: `#/notes?focus=${encodeURIComponent(noteId)}`,
          customData: { noteEntityId: noteId, entityType: "note" },
          label: { text: noteTitle },
        },
      ],
      { regenerateIds: true },
    );
    api.updateScene({ elements: [...current, ...created] });
    api.scrollToContent(created, { fitToContent: true, animate: true });
    setCanvasMessage("Not kartı tuvale eklendi.");
  }

  return (
    <div className="bg-surface" aria-label="Not tuvali">
      <div className="flex flex-wrap items-center gap-1.5 border-b border-subtle px-3 py-2">
        <Button
          size="sm"
          variant="ghost"
          disabled={readOnly || placing || !attachments.length}
          onClick={placeAttachments}
        >
          <Paperclip size={14} /> {placing ? "Yerleştiriliyor" : `Ekleri yerleştir (${attachments.length})`}
        </Button>
        <Button size="sm" variant="ghost" disabled={readOnly} onClick={placeNoteCard}>
          <Link2 size={14} /> Not kartı
        </Button>
        <span className="min-w-2 flex-1" />
        {canvasMessage ? (
          <Chip>{canvasMessage}</Chip>
        ) : (
          <span className="text-meta text-muted">İçe/dışa aktar: tuval menüsü</span>
        )}
      </div>
      <div className="h-[calc(100vh-12rem)] min-h-[36rem] overflow-hidden">
        <Excalidraw
          initialData={initialData}
          name={noteTitle}
          langCode="tr-TR"
          theme={theme}
          viewModeEnabled={readOnly}
          excalidrawAPI={(api) => {
            canvasApi.current = api;
            void hydrateLinkedImages(api).catch(() => setCanvasMessage("Bağlı görseller yüklenemedi."));
          }}
          validateEmbeddable={false}
          handleKeyboardGlobally={false}
          autoFocus
          UIOptions={{
            canvasActions: {
              loadScene: true,
              saveToActiveFile: true,
              toggleTheme: false,
            },
          }}
          onChange={(elements, appState, files) => {
            const next = sceneState(elements, appState, files, linkedFileIds);
            const serialized = JSON.stringify(next);
            if (serialized === lastSaved.current) return;
            pending.current = next;
            if (timer.current) clearTimeout(timer.current);
            timer.current = setTimeout(() => {
              const value = pending.current;
              pending.current = null;
              if (!value) return;
              lastSaved.current = JSON.stringify(value);
              onSaveRef.current(value);
            }, 900);
          }}
        />
      </div>
    </div>
  );
}
