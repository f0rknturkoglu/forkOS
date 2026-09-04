import type { NoteAttachment } from "@/core/types";

type CanvasAttachmentSkeleton = {
  type: "image" | "rectangle";
  x: number;
  y: number;
  width: number;
  height: number;
  link: string;
  fileId?: string;
  label?: { text: string };
  customData: { noteAttachmentId: string; attachmentMime: string };
};

/** Not eklerini Excalidraw'ın dönüştürülebilir sahne taslaklarına çevirir. */
export function attachmentSkeletons(
  attachments: NoteAttachment[],
  alreadyPlaced: Set<string>,
): CanvasAttachmentSkeleton[] {
  return attachments
    .filter((attachment) => !alreadyPlaced.has(attachment.id))
    .map((attachment, index) => {
      const x = 80 + (index % 3) * 360;
      const y = 80 + Math.floor(index / 3) * 240;
      const customData = { noteAttachmentId: attachment.id, attachmentMime: attachment.mime };
      if (attachment.mime.startsWith("image/")) {
        return {
          type: "image",
          x,
          y,
          width: 320,
          height: 200,
          fileId: attachment.id,
          link: attachment.url,
          customData,
        };
      }
      return {
        type: "rectangle",
        x,
        y,
        width: 320,
        height: 96,
        link: attachment.url,
        customData,
        label: { text: `${attachment.name}\n${attachment.mime}` },
      };
    });
}
