/** Silhueta feminina (busto) amostrada em pontos — usada para o efeito de partículas (cenas 3 e 5). */
export type SPt = {x: number; y: number; part: 0 | 1 | 2; r1: number; r2: number; r3: number};

let cache: SPt[] | null = null;
export const FACE = {cx: 540, cy: 890, rx: 118, ry: 150};

export const drawSilhouettePaths = (ctx: CanvasRenderingContext2D, colors: [string, string, string]) => {
  // corpo: pescoço + ombros
  ctx.fillStyle = colors[2];
  ctx.beginPath();
  ctx.moveTo(488, 1000);
  ctx.lineTo(592, 1000);
  ctx.lineTo(600, 1150);
  ctx.bezierCurveTo(740, 1185, 880, 1250, 930, 1400);
  ctx.bezierCurveTo(960, 1480, 975, 1560, 980, 1620);
  ctx.lineTo(100, 1620);
  ctx.bezierCurveTo(105, 1560, 120, 1480, 150, 1400);
  ctx.bezierCurveTo(200, 1250, 340, 1185, 480, 1150);
  ctx.closePath();
  ctx.fill();
  // cabelo longo (atrás)
  ctx.fillStyle = colors[0];
  ctx.beginPath();
  ctx.moveTo(540, 690);
  ctx.bezierCurveTo(690, 690, 735, 800, 730, 930);
  ctx.bezierCurveTo(728, 1060, 770, 1180, 800, 1330);
  ctx.bezierCurveTo(760, 1360, 620, 1330, 540, 1300);
  ctx.bezierCurveTo(460, 1330, 320, 1360, 280, 1330);
  ctx.bezierCurveTo(310, 1180, 352, 1060, 350, 930);
  ctx.bezierCurveTo(345, 800, 390, 690, 540, 690);
  ctx.closePath();
  ctx.fill();
  // rosto
  ctx.fillStyle = colors[1];
  ctx.beginPath();
  ctx.ellipse(FACE.cx, FACE.cy, FACE.rx, FACE.ry, 0, 0, Math.PI * 2);
  ctx.fill();
};

export const getSilhouette = (): SPt[] => {
  if (cache) return cache;
  const c = document.createElement('canvas');
  c.width = 1080;
  c.height = 1920;
  const ctx = c.getContext('2d', {willReadFrequently: true})!;
  drawSilhouettePaths(ctx, ['rgb(255,0,0)', 'rgb(0,255,0)', 'rgb(0,0,255)']);
  const data = ctx.getImageData(0, 0, 1080, 1920).data;
  const out: SPt[] = [];
  let s = 12345;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const step = 7;
  for (let y = 640; y < 1640; y += step) {
    for (let x = 80; x < 1000; x += step) {
      const i = (y * 1080 + x) * 4;
      const a = data[i + 3];
      if (a < 128) continue;
      const part: 0 | 1 | 2 = data[i + 1] > 128 ? 1 : data[i] > 128 ? 0 : 2;
      out.push({x: x + (rnd() - 0.5) * 4, y: y + (rnd() - 0.5) * 4, part, r1: rnd(), r2: rnd(), r3: rnd()});
    }
  }
  cache = out;
  return out;
};

/** malha de escaneamento facial (linhas de latitude/longitude sobre o elipsoide do rosto) */
export const drawFaceMesh = (ctx: CanvasRenderingContext2D, alpha: number, rot: number, scanY: number) => {
  const {cx, cy, rx, ry} = FACE;
  ctx.lineWidth = 1.6;
  for (let i = -5; i <= 5; i++) {
    const yy = cy + (i / 5.6) * ry;
    const w = rx * Math.sqrt(Math.max(0, 1 - Math.pow((yy - cy) / ry, 2)));
    const near = Math.exp(-Math.pow((yy - scanY) / 38, 2));
    ctx.strokeStyle = `rgba(120,200,255,${alpha * (0.35 + near * 0.65)})`;
    ctx.beginPath();
    ctx.ellipse(cx, yy, w, w * 0.16, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
  for (let j = 0; j < 8; j++) {
    const a = rot + (j / 8) * Math.PI;
    const k = Math.cos(a);
    ctx.strokeStyle = `rgba(120,200,255,${alpha * 0.4})`;
    ctx.beginPath();
    ctx.ellipse(cx, cy, Math.abs(k) * rx, ry, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
};
