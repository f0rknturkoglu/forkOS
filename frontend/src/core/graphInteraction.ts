/**
 * Graf tuvalinin gezinme matematigi: kaydirma (pan), yakinlastirma (zoom) ve
 * dugum surukleme icin koordinat cevrimleri.
 *
 * SAF fonksiyonlar -- DOM'a dokunmaz. Boylece "imlecin altindaki nokta
 * yakinlastirinca yerinde kaliyor mu" gibi sorular testle cevaplanabilir;
 * bunlar elle denenmesi zor, kolay bozulan seyler.
 */

export interface Transform {
  /** Tuval kaydirmasi (viewBox birimi). */
  x: number;
  y: number;
  /** Olcek. 1 = birebir. */
  k: number;
}

export const IDENTITY: Transform = { x: 0, y: 0, k: 1 };
export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4;

export function clampZoom(k: number): number {
  if (!Number.isFinite(k)) return 1;
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, k));
}

export interface Point {
  x: number;
  y: number;
}

/** Ekran (viewBox) noktasindan graf koordinatina. */
export function toGraph(point: Point, transform: Transform): Point {
  return { x: (point.x - transform.x) / transform.k, y: (point.y - transform.y) / transform.k };
}

/** Graf koordinatindan ekran (viewBox) noktasina. */
export function toScreen(point: Point, transform: Transform): Point {
  return { x: point.x * transform.k + transform.x, y: point.y * transform.k + transform.y };
}

/**
 * `anchor` ekran noktasini YERINDE tutarak olcegi degistirir.
 * Tekerlekle yakinlastirmada imlecin altindaki dugum kaymaz.
 */
export function zoomAt(transform: Transform, anchor: Point, factor: number): Transform {
  const k = clampZoom(transform.k * factor);
  // Tavana/tabana dayandiysa gercek olcek degismedi; kaydirma da degismemeli.
  const ratio = k / transform.k;
  return {
    k,
    x: anchor.x - (anchor.x - transform.x) * ratio,
    y: anchor.y - (anchor.y - transform.y) * ratio,
  };
}

/** Fare/parmak hareketi kadar tuvali kaydirir. */
export function panBy(transform: Transform, dx: number, dy: number): Transform {
  return { ...transform, x: transform.x + dx, y: transform.y + dy };
}

/**
 * Tarayici piksel koordinatini SVG viewBox koordinatina cevirir.
 * SVG genellikle CSS ile olceklenir; bu oran hesaba katilmazsa surukleme
 * imlecin gerisinde kalir.
 */
export function clientToViewBox(
  client: Point,
  rect: { left: number; top: number; width: number; height: number },
  viewBox: { width: number; height: number },
): Point {
  const scaleX = rect.width > 0 ? viewBox.width / rect.width : 1;
  const scaleY = rect.height > 0 ? viewBox.height / rect.height : 1;
  return { x: (client.x - rect.left) * scaleX, y: (client.y - rect.top) * scaleY };
}
