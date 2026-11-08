import React, {createContext, useContext} from 'react';
import {useCurrentFrame} from 'remotion';
import sync from '../sync.json';
import envelope from '../generated/envelope.json';

export const FPS = 30;
export const EV = sync.events;
export const SC = sync.scenes;

const Ctx = createContext(0);
/** Fornece o quadro GLOBAL (a linha do tempo inteira) a todas as cenas. */
export const GlobalFrame: React.FC<{children: React.ReactNode}> = ({children}) => {
  const f = useCurrentFrame();
  return <Ctx.Provider value={f}>{children}</Ctx.Provider>;
};
export const useG = () => {
  const f = useContext(Ctx);
  return {f, t: f / FPS};
};

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
export const map = (x: number, a: number, b: number, c: number, d: number) => lerp(c, d, clamp((x - a) / (b - a)));
export const easeOut = (k: number) => 1 - Math.pow(1 - clamp(k), 3);
export const easeInOut = (k: number) => {
  k = clamp(k);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
export const easeOutBack = (k: number) => {
  k = clamp(k);
  const c1 = 1.70158, c3 = c1 + 1;
  return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2);
};
/** 0→1 ao longo de [a,b] segundos */
export const prog = (t: number, a: number, b: number) => clamp((t - a) / (b - a));

/** PRNG determinístico (mulberry32) — mesmos resultados em qualquer renderização */
export const rng = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};
/** ruído suave 1D determinístico */
export const noise1 = (x: number, seed = 0) =>
  Math.sin(x * 1.7 + seed * 12.9898) * 0.5 + Math.sin(x * 3.1 + seed * 78.233) * 0.3 + Math.sin(x * 5.3 + seed * 3.17) * 0.2;

type Env = typeof envelope;
const E = envelope as Env;
/** Envelope de áudio (0..1) por frame: 'voice' | 'call' | 'music' | 'sfx' */
export const envAt = (kind: 'voice' | 'call' | 'music' | 'sfx', f: number) => {
  const arr = E[kind] as number[];
  const i = clamp(Math.floor(f), 0, arr.length - 1);
  return arr[i];
};
/** Amplitude da fala (voz + ligação) em resolução 4x por quadro, interpolada */
export const voiceAmp = (t: number) => {
  const arr = E.hires as number[];
  const x = clamp(t * FPS * E.sub, 0, arr.length - 1);
  const i = Math.floor(x);
  return lerp(arr[i], arr[Math.min(i + 1, arr.length - 1)], x - i);
};

/** Tremor de câmera: soma de impactos amortecidos nos instantes dados */
export const shakeAt = (t: number, hits: {at: number; amp: number; decay?: number}[]) => {
  let x = 0, y = 0, r = 0;
  for (const h of hits) {
    const d = t - h.at;
    if (d < 0 || d > 1.2) continue;
    const a = h.amp * Math.exp(-d * (h.decay ?? 7));
    x += Math.sin(d * 97 + h.at) * a;
    y += Math.cos(d * 83 + h.at * 2) * a;
    r += Math.sin(d * 61 + h.at * 3) * a * 0.02;
  }
  return {x, y, r};
};

/** Janela de opacidade [a..b] com fades de entrada/saída (s) */
export const win = (t: number, a: number, b: number, fi = 0.25, fo = 0.25) =>
  clamp(Math.min((t - a) / Math.max(fi, 1e-3), (b - t) / Math.max(fo, 1e-3)));
