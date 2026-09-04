import { describe, expect, it } from "vitest";
import { attachmentSkeletons } from "./canvasAttachments";

describe("not tuvali ek yerleşimi", () => {
  const image = {
    id: "image-1",
    name: "mimari.png",
    mime: "image/png",
    size: 120,
    url: "/api/notes/note-1/attachments/image-1",
  };
  const audio = {
    id: "audio-1",
    name: "fikir.m4a",
    mime: "audio/mp4",
    size: 240,
    url: "/api/notes/note-1/attachments/audio-1",
  };

  it("görseli gerçek image, diğer ekleri bağlantılı kart olarak üretir", () => {
    const result = attachmentSkeletons([image, audio], new Set());

    expect(result[0]).toMatchObject({
      type: "image",
      fileId: "image-1",
      link: image.url,
      customData: { noteAttachmentId: "image-1" },
    });
    expect(result[1]).toMatchObject({
      type: "rectangle",
      link: audio.url,
      customData: { noteAttachmentId: "audio-1" },
      label: { text: "fikir.m4a\naudio/mp4" },
    });
  });

  it("tuvalde bulunan eki yeniden üretmez", () => {
    expect(attachmentSkeletons([image, audio], new Set(["image-1"]))).toHaveLength(1);
  });
});
