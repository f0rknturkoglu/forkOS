/**
 * Kucuk kuvvet-yonlendirmeli yerlesim (force-directed layout).
 *
 * Neden kendi kodumuz: d3-force gibi bir kutuphane giris paketine yuzlerce KB
 * ekler; bize gereken tek sey birkac yuz dugumu okunur bicimde dagitmak.
 * Fonksiyon SAF ve DETERMINISTIK -- ayni graf her seferinde ayni yerlesimi
 * verir (rastgele tohum yok), boylece test edilebilir ve ekran zıplamaz.
 */

interface LayoutNode {
  id: string;
  degree: number;
}

interface LayoutEdge {
  from: string;
  to: string;
}

interface Placed {
  id: string;
  x: number;
  y: number;
  r: number;
}

interface LayoutOptions {
  width?: number;
  height?: number;
  iterations?: number;
}

/** Dugum yaricapi: baglanti sayisi arttikca buyur, ama sinirli. */
export function nodeRadius(degree: number): number {
  return Math.min(16, 5 + Math.sqrt(degree) * 2.6);
}

export function layoutGraph(nodes: LayoutNode[], edges: LayoutEdge[], options: LayoutOptions = {}): Placed[] {
  const width = options.width ?? 800;
  const height = options.height ?? 520;
  const count = nodes.length;
  if (count === 0) return [];

  const centerX = width / 2;
  const centerY = height / 2;
  if (count === 1) return [{ id: nodes[0].id, x: centerX, y: centerY, r: nodeRadius(nodes[0].degree) }];

  // Baslangic: cember uzerinde esit araliklarla (deterministik).
  const radius = Math.min(width, height) * 0.36;
  const points = nodes.map((node, index) => {
    const angle = (index / count) * Math.PI * 2;
    return {
      id: node.id,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      r: nodeRadius(node.degree),
    };
  });
  const index = new Map(points.map((point, i) => [point.id, i]));

  // Dugum sayisi arttikca adim sayisi duser -- cizim maliyeti sinirli kalsin.
  const steps = options.iterations ?? Math.max(80, Math.min(300, Math.round(4200 / count)));
  // Dengedeki komsu araligi (Fruchterman-Reingold "k").
  const ideal = Math.sqrt((width * height) / count) * 0.62;
  // Adim tavani k'DEN BAGIMSIZ: k buyuk oldugunda (az dugum) tek adimda
  // duvara ucup orada kalmasin diye tuvale gore olculur.
  const heat = Math.min(width, height) * 0.12;

  for (let step = 0; step < steps; step += 1) {
    // Sogutma: adimlar ilerledikce hareket kuculur, yerlesim oturur.
    const cooling = 1 - step / steps;
    const dx = new Float64Array(count);
    const dy = new Float64Array(count);

    // Itme: her cift birbirini uzaklastirir.
    for (let i = 0; i < count; i += 1) {
      for (let j = i + 1; j < count; j += 1) {
        let ox = points[i].x - points[j].x;
        let oy = points[i].y - points[j].y;
        let dist = Math.hypot(ox, oy);
        if (dist < 0.01) {
          // Ust uste dusen dugumleri deterministik bir yone it.
          ox = (i - j) % 2 === 0 ? 0.5 : -0.5;
          oy = 0.5;
          dist = 0.71;
        }
        const force = (ideal * ideal) / dist;
        const fx = (ox / dist) * force;
        const fy = (oy / dist) * force;
        dx[i] += fx;
        dy[i] += fy;
        dx[j] -= fx;
        dy[j] -= fy;
      }
    }

    // Cekme: kenarlar uclarini birbirine yaklastirir.
    for (const edge of edges) {
      const a = index.get(edge.from);
      const b = index.get(edge.to);
      if (a === undefined || b === undefined || a === b) continue;
      const ox = points[a].x - points[b].x;
      const oy = points[a].y - points[b].y;
      const dist = Math.max(0.01, Math.hypot(ox, oy));
      const force = (dist * dist) / ideal;
      const fx = (ox / dist) * force;
      const fy = (oy / dist) * force;
      dx[a] -= fx;
      dy[a] -= fy;
      dx[b] += fx;
      dy[b] += fy;
    }

    const maxStep = heat * cooling * cooling;
    for (let i = 0; i < count; i += 1) {
      // Merkeze cekim: kopuk kumeleri iceride tutan tek kuvvet bu.
      dx[i] += (centerX - points[i].x) * 0.22;
      dy[i] += (centerY - points[i].y) * 0.22;
      const move = Math.hypot(dx[i], dy[i]);
      const scale = move > maxStep ? maxStep / move : 1;
      points[i].x += dx[i] * scale;
      points[i].y += dy[i] * scale;
    }
    // NOT: dongu icinde kenara KIRPMA YOK. Kirpmak, duvara dayanan dugumun
    // disari bileseni sifirlandigi icin onu orada kilitliyordu (regresyon:
    // butun kume alt kenara diziliyordu). Sinira yalnizca en sonda cekilir.
  }
  return fitToCanvas(points, width, height);
}

/**
 * Simulasyon GORELI yapiyi kurar; olcek ve konum burada verilir.
 *
 * Neden kirpma degil de sigdirma: kirpma, duvara dayanan dugumun disari
 * bilesenini sifirlar ve onu orada kilitler -- butun kume kenara diziliyordu.
 * Sigdirma ile hem yapisma imkansiz olur hem de tuvalin tamami kullanilir.
 */
function fitToCanvas(points: Placed[], width: number, height: number): Placed[] {
  const margin = Math.max(...points.map((point) => point.r)) + 14;
  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  const minY = Math.min(...points.map((p) => p.y));
  const maxY = Math.max(...points.map((p) => p.y));
  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const usableW = Math.max(1, width - margin * 2);
  const usableH = Math.max(1, height - margin * 2);
  // Tek eksende yigilmis (ya da tek dugumlu) yerlesimde bolme yapilmaz.
  const scale = Math.min(
    spanX > 0.001 ? usableW / spanX : Number.POSITIVE_INFINITY,
    spanY > 0.001 ? usableH / spanY : Number.POSITIVE_INFINITY,
  );
  const factor = Number.isFinite(scale) ? scale : 1;
  // Olceklenmis icerigi tuvalde ortala.
  const offsetX = (width - spanX * factor) / 2 - minX * factor;
  const offsetY = (height - spanY * factor) / 2 - minY * factor;
  for (const point of points) {
    point.x = point.x * factor + offsetX;
    point.y = point.y * factor + offsetY;
  }
  return points;
}
