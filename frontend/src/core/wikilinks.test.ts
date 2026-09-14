import { describe, expect, it } from "vitest";
import { completeWikilink, openWikilinkQuery } from "./wikilinks";

describe("[[ ]] otomatik tamamlama", () => {
  it("imlecin solunda açık bir [[ varsa yazılan parçayı verir", () => {
    expect(openWikilinkQuery("Bugün [[line", 12)).toBe("line");
    expect(openWikilinkQuery("[[", 2)).toBe("");
  });

  it("kapanmış ya da satır atlamış bağlantıyı açık saymaz", () => {
    expect(openWikilinkQuery("[[Bitti]] devam", 15)).toBeNull();
    expect(openWikilinkQuery("[[yarım\nsonraki", 15)).toBeNull();
    expect(openWikilinkQuery("hiç köşeli yok", 5)).toBeNull();
  });

  it("imlecin sağındaki metni hesaba katmaz", () => {
    // Imlec "[[ma" sonunda (4. karakter); sagdaki metin acikligi degistirmez.
    expect(openWikilinkQuery("[[ma ve sonra ]] var", 4)).toBe("ma");
    // Baslikta bosluk olabilir: parca boslukla da devam edebilir.
    expect(openWikilinkQuery("[[Lineer Ce", 11)).toBe("Lineer Ce");
  });

  it("yarım yazılanı tam başlıkla değiştirir ve imleci sonuna alır", () => {
    const result = completeWikilink("Bugün [[line", 12, "Lineer Cebir");
    expect(result.value).toBe("Bugün [[Lineer Cebir]]");
    expect(result.caret).toBe(result.value.length);
  });

  it("imlecin sağındaki metni korur", () => {
    const result = completeWikilink("[[ka çalıştım", 4, "Kalkülüs");
    expect(result.value).toBe("[[Kalkülüs]] çalıştım");
    // Imlec eklenen baglantinin hemen sonunda.
    expect(result.value.slice(result.caret)).toBe(" çalıştım");
  });

  it("açık bağlantı yoksa metni bozmaz", () => {
    expect(completeWikilink("düz metin", 4, "X")).toEqual({ value: "düz metin", caret: 4 });
  });
});
