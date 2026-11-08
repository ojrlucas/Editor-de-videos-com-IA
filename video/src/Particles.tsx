import React, {useLayoutEffect, useRef} from 'react';
import {W, H, clamp, lerp, range, smooth} from './timeline';
import {shardFastPhase, shardSlowPhase, TL} from './anim';

const mulberry = (a: number) => () => {
  a |= 0; a = (a + 0x6d2b79f5) | 0;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

const NP = 520;
const rng = mulberry(1189733);
const P = Array.from({length: NP}, () => ({
  x: rng(), y: rng(), z: Math.pow(rng(), 1.6), len: 0.4 + rng() * 1.2, ph: rng() * 6.28, hue: rng(), tw: 2 + rng() * 6,
  show: rng(),
}));
const NH = 11;
const HERO = Array.from({length: NH}, (_, i) => ({
  x: rng(), y: 0.12 + rng() * 0.7, z: 0.45 + rng() * 0.55, size: 70 + rng() * 150, rot: rng() * 6.28, spin: (rng() - 0.5) * 0.8,
  flip: rng() * 6.28, fs: 0.4 + rng() * 0.9, n: 5 + Math.floor(rng() * 3), seed: i * 17 + 3, sc: rng(),
  rad: Array.from({length: 7}, () => 0.55 + rng() * 0.6),
}));

/** Densidade de partículas por cena. */
const density = (t: number) => {
  if (t < 4.6) return 0;
  if (t < 8.1) return 0.18 + 0.55 * smooth(range(t, 5.2, 8));
  if (t < 13.1) return 1;
  if (t < 13.6) return 1 - range(t, 13.1, 13.6);
  if (t < 18.4) return 0;
  return 0.55 + 0.45 * smooth(range(t, 18.8, 24));
};
const heroAmt = (t: number) => {
  if (t < 6.2) return 0;
  if (t < 8.1) return 0.5 * smooth(range(t, 6.2, 7.5));
  if (t < 13.0) return 1;
  if (t < 13.5) return 1 - range(t, 13, 13.5);
  if (t < 18.8) return 0;
  return 0.65 * smooth(range(t, 19, 20.5));
};

export const Particles: React.FC<{t: number}> = ({t}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const c = ref.current!;
    const ctx = c.getContext('2d')!;
    ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    const dens = density(t);
    const fast = shardFastPhase(t);
    // inclinação do vento (as partículas descem levemente)
    const slope = 0.16;
    const wideW = W + 600;
    const intens = clamp(0.4 + dens, 0, 1.2);
    // ---------- partículas de silicato (rápidas, com rastro de movimento)
    if (dens > 0) {
      for (let i = 0; i < NP; i++) {
        const p = P[i];
        if (p.show > dens) continue;
        const z = p.z;
        const mul = 0.25 + 1.5 * z * z + 0.2;
        const dist = fast * mul;
        const x = ((p.x * wideW - dist) % wideW + wideW) % wideW - 300;
        const y = (p.y * (H + 400) + dist * slope * (0.5 + z)) % (H + 400) - 200;
        const speedPx = (1500 * 0.6) * mul;       // px/s aproximada
        const streak = Math.min(520, speedPx * 0.05 * p.len * (t > 8 && t < 13.2 ? 2.4 : 1.4) + 10);
        const size = 2 + 7 * z * z + 1.5 * z;
        const focus = 0.55;
        const blur = Math.abs(z - focus) * 14 * (z > focus ? 1.6 : 0.8);
        const tw = 0.65 + 0.35 * Math.sin(t * p.tw + p.ph);
        const a = Math.min(1.4, (0.55 + 0.9 * z) * tw * Math.min(1, dens * 1.4) * 1.5);
        const ang = Math.atan2(slope * (0.5 + z), -1);
        const dx = Math.cos(ang), dy = Math.sin(ang);
        const warm = p.hue > 0.88;
        const col = warm ? '255,226,190' : p.hue > 0.45 ? '190,230,255' : '120,190,255';
        if (blur > 4.5 && z > focus) {
          // bokeh (desfocado, perto da câmera)
          const r = size * 2.2 + blur * 1.2;
          const g = ctx.createRadialGradient(x, y, 0, x, y, r);
          g.addColorStop(0, `rgba(${col},${0.22 * a})`);
          g.addColorStop(0.7, `rgba(${col},${0.12 * a})`);
          g.addColorStop(1, `rgba(${col},0)`);
          ctx.fillStyle = g;
          ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
          continue;
        }
        const x0 = x - dx * streak * -1, y0 = y - dy * streak * -1; // cauda atrás da direção de movimento
        const gr = ctx.createLinearGradient(x, y, x0, y0);
        gr.addColorStop(0, `rgba(${col},${0.95 * a})`);
        gr.addColorStop(0.15, `rgba(${col},${0.5 * a})`);
        gr.addColorStop(1, `rgba(${col},0)`);
        ctx.strokeStyle = gr;
        ctx.lineCap = 'round';
        ctx.lineWidth = size * (blur > 2 ? 1 + blur * 0.15 : 1);
        ctx.globalAlpha = blur > 2 ? 0.6 : 1;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x0, y0); ctx.stroke();
        ctx.globalAlpha = 1;
        // brilho da cabeça
        if (z > 0.3) {
          const r = size * 3.2;
          const g = ctx.createRadialGradient(x, y, 0, x, y, r);
          g.addColorStop(0, `rgba(255,255,255,${0.55 * a})`);
          g.addColorStop(1, `rgba(${col},0)`);
          ctx.fillStyle = g;
          ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
        }
      }
    }
    // ---------- fragmentos de cristal em câmera lenta (grandes, com profundidade de campo)
    const ha = heroAmt(t);
    if (ha > 0) {
      const slow = shardSlowPhase(t);
      const order = HERO.map((h, i) => i).sort((a, b) => HERO[a].z - HERO[b].z);
      for (const i of order) {
        const h = HERO[i];
        if (h.sc > ha + 0.35) continue;
        const wW = W + 700;
        const x = ((h.x * wW - slow * (0.6 + h.z * 1.6)) % wW + wW) % wW - 350;
        const y = h.y * H + Math.sin(t * 0.7 + h.seed) * 40 + slow * 0.12 * h.z;
        const size = h.size * (0.55 + h.z * 0.9);
        const rot = h.rot + t * h.spin;
        const flipx = Math.cos(h.flip + t * h.fs);
        const blur = Math.abs(h.z - 0.62) * 22;
        const al = Math.min(1, ha * 1.2) * (0.55 + 0.45 * h.z);
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        ctx.filter = blur > 0.8 ? `blur(${blur.toFixed(1)}px)` : 'none';
        ctx.translate(x, y);
        ctx.rotate(rot);
        ctx.scale(Math.max(0.18, Math.abs(flipx)), 1);
        // contorno irregular (cristal)
        const n = h.n;
        const pts: [number, number][] = [];
        for (let k = 0; k < n; k++) {
          const a = (k / n) * 6.2832;
          const r = size * h.rad[k] * (k % 2 ? 0.55 : 1) * (k === 0 ? 1.7 : 1);
          pts.push([Math.cos(a) * r * 0.5, Math.sin(a) * r * 0.5]);
        }
        const g = ctx.createLinearGradient(-size * 0.5, -size * 0.5, size * 0.5, size * 0.5);
        g.addColorStop(0, `rgba(225,246,255,${0.85 * al})`);
        g.addColorStop(0.45, `rgba(80,160,255,${0.40 * al})`);
        g.addColorStop(1, `rgba(200,236,255,${0.75 * al})`);
        ctx.fillStyle = g;
        ctx.beginPath(); pts.forEach(([px, py], k) => (k ? ctx.lineTo(px, py) : ctx.moveTo(px, py))); ctx.closePath(); ctx.fill();
        // facetas internas
        ctx.strokeStyle = `rgba(220,245,255,${0.85 * al})`;
        ctx.lineWidth = Math.max(1.2, size * 0.014);
        ctx.lineJoin = 'round';
        ctx.stroke();
        ctx.beginPath();
        pts.forEach(([px, py], k) => { if (k % 2 === 0) { ctx.moveTo(0, 0); ctx.lineTo(px, py); } });
        ctx.strokeStyle = `rgba(160,215,255,${0.28 * al})`; ctx.stroke();
        // brilho especular que varre a face
        const sweep = Math.sin(t * 1.3 + h.seed) * 0.5 + 0.5;
        const sg = ctx.createRadialGradient(pts[0][0] * sweep, pts[0][1] * sweep, 0, 0, 0, size * 0.5);
        sg.addColorStop(0, `rgba(255,255,255,${0.55 * al})`); sg.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = sg;
        ctx.beginPath(); pts.forEach(([px, py], k) => (k ? ctx.lineTo(px, py) : ctx.moveTo(px, py))); ctx.closePath(); ctx.fill();
        ctx.filter = 'none';
        // reflexo em cruz (apenas fragmentos nítidos)
        if (blur < 6) {
          const fl = Math.max(0, Math.sin(t * 2.2 + h.seed * 1.7));
          const L = size * (0.55 + 1.4 * fl * fl);
          ctx.rotate(-rot);
          ctx.strokeStyle = `rgba(255,255,255,${0.7 * fl * al})`;
          ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(-L, 0); ctx.lineTo(L, 0); ctx.moveTo(0, -L * 0.6); ctx.lineTo(0, L * 0.6); ctx.stroke();
        }
        ctx.restore();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
  });
  return <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} />;
};
