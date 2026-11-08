import {clamp, lerp, range, smooth, smoother, FPS, DURATION_S} from './timeline';
import timeline from '../public/timeline.json';

export const TL = timeline as {
  sentences: {i: number; text: string; start: number; end: number; words: {w: string; hl: number; s: number; e: number}[]}[];
  flashes: number[];
  ticks: number[];
  impacts: number[];
};

// ---------- integrais numéricas (fases contínuas, sem saltos ao mudar a velocidade)
const STEP = 1 / 240;
const integrate = (f: (t: number) => number) => {
  const n = Math.ceil((DURATION_S + 1) / STEP);
  const a = new Float64Array(n + 1);
  for (let i = 1; i <= n; i++) a[i] = a[i - 1] + f((i - 0.5) * STEP) * STEP;
  return (t: number) => {
    const x = clamp(t / STEP, 0, n - 1);
    const i = Math.floor(x);
    return lerp(a[i], a[i + 1], x - i);
  };
};

// ---------- velocidade de avanço pela nuvem (profundidade/s) — com rampas de câmera lenta/rápida
export const flySpeed = (t: number) => {
  if (t < 4) return 0.05;
  if (t < 8) return lerp(0.55, 0.22, smooth(range(t, 4.1, 6)));            // mergulho rápido e desacelera
  if (t < 13.5) {
    const slow = 1 - 0.8 * smooth(range(t, 9.4, 9.9)) * (1 - smooth(range(t, 11.3, 11.9))); // bullet-time
    const fast = 1 + 1.4 * smooth(range(t, 11.7, 12.4));
    return 0.34 * slow * fast + 0.06;
  }
  if (t < 18) return 0.05;
  return lerp(0.25, 0.75, smooth(range(t, 18.2, 24.5)));                    // aproximação do vórtice
};
export const windSpeed = (t: number) => {
  if (t < 4.2) return 0.1;
  if (t < 8) return lerp(0.18, 0.5, smooth(range(t, 4.4, 8)));
  if (t < 13.5) {
    const gust = 1 + 0.35 * Math.sin(t * 1.9) * Math.sin(t * 0.7 + 1);
    const slow = 1 - 0.75 * smooth(range(t, 9.4, 9.9)) * (1 - smooth(range(t, 11.3, 11.9)));
    return 1.55 * gust * (0.35 + 0.65 * slow) * (1 + 0.5 * smooth(range(t, 11.7, 12.5)));
  }
  if (t < 18) return 0.1;
  return lerp(0.5, 0.95, smooth(range(t, 18.4, 24)));
};
export const flyPhase = integrate(flySpeed);
export const windPhase = integrate(windSpeed);
// movimento "rápido" das partículas (px) e "lento" dos fragmentos de cristal (câmera lenta)
export const shardFastPhase = integrate((t) => windSpeed(t) * 1500 + 90);
export const shardSlowPhase = integrate((t) => {
  const s = t < 8 ? 40 : t < 13.5 ? 38 + 60 * smooth(range(t, 12, 13)) : 30;
  return s + 22 * Math.sin(t * 0.9);
});

// ---------- cena 1: viagem até o planeta (0 – 4.4 s)
export const planetA = (t: number) => {
  const s = clamp(t / 4.4);
  const R = 0.04 * Math.exp(0.98 * t * (4.4 / 4.4));
  const top = lerp(0.3, 2.6, smoother(range(s, 0.3, 1)));
  const cx = 0.14 * (1 - smooth(range(s, 0, 0.85)));
  return {R, C: [cx, top - R] as [number, number], rot: t * 1.1, zoom: t * 1.0, grid: 0, detail: smooth(range(t, 2.5, 4.4)) * 2};
};

// ---------- cena 4: recuo e visão do planeta inteiro (12.9 – 18.6 s)
export const planetD = (t: number) => {
  const R0 = 3.4, Rend = 0.74;
  const pull = smoother(range(t, 13.0, 16.4));
  let R = Math.exp(lerp(Math.log(R0), Math.log(Rend), pull));
  R *= 1 - 0.035 * smooth(range(t, 16.4, 17.5));      // deriva lenta
  const push = smoother(range(t, 17.25, 18.6));
  R = R * Math.exp(Math.log(4.2 / 0.7) * push);
  const cy = lerp(-1.3, 0.30, pull) + push * -0.35;
  const cx = lerp(0.0, 0.0, pull);
  return {R, C: [cx, cy] as [number, number], rot: 20 + t * 1.1, zoom: -2.5 + (t - 13) * 0.2, grid: smooth(range(t, 15.0, 16.0)) * (1 - smooth(range(t, 17.5, 18.1))), detail: 1};
};

// ---------- relâmpagos (sincronizados com os trovões do áudio)
export const flashAt = (t: number) => {
  let f = 0;
  for (const tf of TL.flashes) {
    const d = t - tf;
    if (d >= 0) f += Math.exp(-d / 0.09) * 0.55 + (d > 0.13 ? Math.exp(-(d - 0.13) / 0.14) * 0.8 : 0);
  }
  return Math.min(f, 1.1);
};

// ---------- tremor de câmera (impactos + vento)
const n1 = (x: number) => Math.sin(x * 12.9898) * 43758.5453 % 1;
export const shakeAt = (t: number): [number, number] => {
  let a = 0;
  if (t >= 8.1 && t < 13.2) a += 0.0035 + 0.0045 * smooth(range(t, 11.7, 12.4));
  if (t >= 19 && t < 25) a += 0.0025 * smooth(range(t, 19, 24));
  for (const ti of TL.impacts) { const d = t - ti; if (d >= 0 && d < 0.5) a += 0.02 * Math.exp(-d * 9); }
  for (const tf of TL.flashes) { const d = t - tf; if (d >= 0 && d < 0.4) a += 0.012 * Math.exp(-d * 10); }
  return [Math.sin(t * 61) * a + Math.sin(t * 23.7) * a * 0.6, Math.cos(t * 53) * a + Math.sin(t * 31.1) * a * 0.5];
};

// ---------- transições
export const tClouds1 = {in: 3.85, out: 13.4};        // nuvens (cenas 2 e 3)
export const tPlanetD = {in: 12.85, out: 18.7};       // planeta inteiro (cena 4)
export const tClouds2 = {in: 18.0};                   // tempestade final (cena 5)
export const fps = FPS;
