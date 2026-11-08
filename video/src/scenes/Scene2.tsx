import React from 'react';
import {C, F, W, H} from '../theme';
import {Canvas2D, glowSprite} from '../components/Canvas2D';
import {AmbientBG} from '../components/Overlays';
import {EV, clamp, easeInOut, easeOut, lerp, map, noise1, prog, rng, shakeAt, useG, voiceAmp, win} from '../lib/time';

const CORE = {x: 540, y: 1100};
const WAVE_Y = 735;
const BARS = 64;
const N_FR = EV.fragmentCount;

const parts = (() => {
  const r = rng(5);
  return Array.from({length: 190}, () => ({x: r() * W, y: r() * H, z: 0.2 + r() * 0.8, s: 1 + r() * 3, ph: r() * 6, blue: r() > 0.18}));
})();
const frags = Array.from({length: N_FR}, (_, i) => {
  const r = rng(100 + i);
  const bar = Math.floor(r() * BARS);
  return {bar, tA: EV.fragmentStart + i * EV.fragmentStep, flight: 0.62 + r() * 0.2, bend: (r() - 0.5) * 380};
});
const hexLines = (() => {
  const r = rng(9);
  return Array.from({length: 40}, () => Array.from({length: 4}, () => Math.floor(r() * 65535).toString(16).padStart(4, '0').toUpperCase()).join(' '));
})();

const barX = (i: number) => 120 + (i / (BARS - 1)) * 840;
const barAmp = (t: number, i: number) => {
  const v = voiceAmp(t - 0.02 * Math.abs(i - BARS / 2) * 0.35);
  const shape = 0.5 + 0.5 * Math.sin(i * 0.55 + t * 9) * Math.cos(i * 0.21 - t * 4.3);
  const env = Math.sin((i / (BARS - 1)) * Math.PI) ** 0.7;
  return (0.12 + 0.88 * (0.25 + 0.75 * v) * (0.35 + 0.65 * shape)) * (0.35 + 0.65 * env);
};

/** CENA 2 — Captura da voz (3–7s): ondas femininas → fragmentos → núcleo de IA. */
export const Scene2: React.FC = () => {
  const {t, f} = useG();
  const lt = t - 3.0;
  const cam = easeInOut(prog(t, 3.0, 7.2));
  const scale = lerp(1.0, 1.12, cam);
  const drift = noise1(t * 0.6) * 10;
  const sh = shakeAt(t, [{at: EV.glitch12, amp: 18}]);
  const op = win(t, 3.0, 7.4, 0.001, 0.001);
  const progress = clamp(map(t, EV.fragmentStart, EV.fragmentStart + (N_FR - 1) * EV.fragmentStep + 0.4, 0, 1));
  const pulse = frags.reduce((a, fr) => a + (t > fr.tA ? Math.exp(-(t - fr.tA) * 9) : 0), 0);

  return (
    <div style={{position: 'absolute', inset: 0, opacity: op}}>
      <AmbientBG blue={0.2} red={0.04} cx={50} cy={56} />
      <div style={{position: 'absolute', inset: 0, transform: `translate(${sh.x + drift}px,${sh.y}px) scale(${scale})`, transformOrigin: '50% 58%'}}>
        {/* camada de fundo: partículas + grade (parallax) */}
        <Canvas2D
          draw={(ctx) => {
            // chão em grade digital
            const hy = 1180;
            ctx.lineWidth = 1.5;
            const phase = (t * 0.9) % 1;
            for (let i = 0; i < 26; i++) {
              const k = (i + phase) / 26;
              const y = hy + 760 * Math.pow(k, 2.3);
              ctx.strokeStyle = `rgba(8,126,255,${0.04 + 0.34 * k})`;
              ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
            }
            for (let i = -14; i <= 14; i++) {
              ctx.strokeStyle = `rgba(8,126,255,${0.2 - Math.abs(i) * 0.008})`;
              ctx.beginPath(); ctx.moveTo(540 + i * 14, hy); ctx.lineTo(540 + i * 230, H + 20); ctx.stroke();
            }
            const g = ctx.createLinearGradient(0, hy - 120, 0, hy + 80);
            g.addColorStop(0, 'rgba(5,6,9,0)'); g.addColorStop(1, 'rgba(8,126,255,0.12)');
            ctx.fillStyle = g; ctx.fillRect(0, hy - 120, W, 200);
            // partículas flutuantes em 3 profundidades
            ctx.globalCompositeOperation = 'lighter';
            parts.forEach((p) => {
              const px = (p.x + Math.sin(t * 0.5 * p.z + p.ph) * 40 * p.z) % W;
              const py = (p.y - t * 26 * p.z + H * 4) % H;
              const a = (0.25 + 0.55 * p.z) * (0.6 + 0.4 * Math.sin(t * 3 + p.ph));
              const s = p.s * 8 * p.z + 6;
              ctx.drawImage(glowSprite(p.blue ? `rgba(60,160,255,${a})` : `rgba(255,70,90,${a * 0.7})`, 64), px - s / 2, py - s / 2, s, s);
            });
            // colunas de dados hexadecimais
            ctx.globalCompositeOperation = 'source-over';
            ctx.font = `400 22px ${F.mono}`;
            for (let side = 0; side < 2; side++) {
              for (let i = 0; i < 18; i++) {
                const y = ((i * 46 - t * 60) % (H + 100) + H + 100) % (H + 100) - 50;
                ctx.fillStyle = `rgba(90,170,255,${0.07 + 0.1 * Math.sin(t * 2 + i)})`;
                ctx.fillText(hexLines[(i + side * 7) % 40], side ? 800 : 30, y);
              }
            }
          }}
        />
        {/* moldura da interface de entrada de áudio */}
        <Canvas2D
          draw={(ctx) => {
            const a = clamp(lt / 0.5);
            // cantoneiras
            ctx.strokeStyle = `rgba(80,170,255,${0.8 * a})`;
            ctx.lineWidth = 3;
            const x0 = 70, x1 = 1010, y0 = WAVE_Y - 150, y1 = WAVE_Y + 150, L = 46;
            [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(([x, y, dx, dy]) => {
              ctx.beginPath(); ctx.moveTo(x, y + dy * L); ctx.lineTo(x, y); ctx.lineTo(x + dx * L, y); ctx.stroke();
            });
            ctx.font = `700 22px ${F.mono}`;
            ctx.fillStyle = `rgba(120,190,255,${0.9 * a})`;
            ctx.fillText('ENTRADA DE ÁUDIO  ·  VOZ FEMININA', x0 + 14, y0 - 16);
            ctx.textAlign = 'right';
            ctx.fillStyle = `rgba(255,70,90,${(0.6 + 0.4 * Math.sin(t * 8)) * a})`;
            ctx.fillText('● CAPTURANDO', x1 - 6, y0 - 16);
            ctx.textAlign = 'left';

            // barras de onda sonora, reagindo ao áudio
            ctx.globalCompositeOperation = 'lighter';
            for (let i = 0; i < BARS; i++) {
              const x = barX(i);
              const amp = barAmp(t, i);
              // barras extraídas por fragmentos "levantam" e brilham
              let ext = 0;
              frags.forEach((fr) => { if (fr.bar === i) { const d = t - (fr.tA - fr.flight); if (d > -0.1 && d < 0.5) ext = Math.max(ext, 1 - Math.abs(d - 0.1) / 0.45); } });
              const h = amp * 125 * (0.9 + ext * 0.4);
              const col = ext > 0.01 ? `rgba(${Math.round(120 + 135 * ext)},${Math.round(190 + 65 * ext)},255,${0.9})` : 'rgba(8,126,255,0.85)';
              ctx.fillStyle = col;
              ctx.fillRect(x - 5, WAVE_Y - h, 10, h * 2);
              ctx.fillStyle = 'rgba(8,126,255,0.12)';
              ctx.fillRect(x - 10, WAVE_Y - h * 1.15, 20, h * 2.3);
              ctx.fillStyle = 'rgba(210,235,255,0.7)';
              ctx.fillRect(x - 2, WAVE_Y - h * 0.6, 4, h * 1.2);
            }
            ctx.globalCompositeOperation = 'source-over';
            ctx.fillStyle = 'rgba(80,170,255,0.5)';
            ctx.fillRect(100, WAVE_Y - 1, 880, 2);
          }}
        />
        {/* fragmentos luminosos conduzidos ao núcleo + núcleo digital */}
        <Canvas2D
          draw={(ctx) => {
            ctx.globalCompositeOperation = 'lighter';
            frags.forEach((fr) => {
              const d = (t - (fr.tA - fr.flight)) / fr.flight;
              if (d < 0 || d > 1.05) return;
              const sx = barX(fr.bar), sy = WAVE_Y;
              const cx = (sx + CORE.x) / 2 + fr.bend, cy = (sy + CORE.y) / 2 - 40;
              const at = (k: number) => {
                const kk = easeInOut(clamp(k));
                const u = 1 - kk;
                return {x: u * u * sx + 2 * u * kk * cx + kk * kk * CORE.x, y: u * u * sy + 2 * u * kk * cy + kk * kk * CORE.y};
              };
              for (let s = 0; s < 14; s++) {
                const p = at(d - s * 0.018);
                const a = (1 - s / 14) * (d < 1 ? 1 : 0.4);
                const sz = (30 - s * 1.5) * (1 + 0.2 * Math.sin(f + s));
                ctx.drawImage(glowSprite(s < 2 ? `rgba(230,245,255,${a})` : `rgba(60,160,255,${a * 0.8})`, 64), p.x - sz / 2, p.y - sz / 2, sz, sz);
              }
            });
            // ---- núcleo
            const R = 92 * (1 + pulse * 0.07);
            const rot = t * 0.9;
            const halo = 520 + pulse * 140;
            ctx.drawImage(glowSprite(`rgba(8,126,255,${0.5 + pulse * 0.2})`, 128), CORE.x - halo / 2, CORE.y - halo / 2, halo, halo);
            ctx.globalCompositeOperation = 'source-over';
            const g = ctx.createRadialGradient(CORE.x - 25, CORE.y - 30, 6, CORE.x, CORE.y, R);
            g.addColorStop(0, 'rgba(230,245,255,1)'); g.addColorStop(0.35, 'rgba(60,160,255,0.95)'); g.addColorStop(1, 'rgba(6,40,120,0.95)');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(CORE.x, CORE.y, R, 0, Math.PI * 2); ctx.fill();
            ctx.save();
            ctx.beginPath(); ctx.arc(CORE.x, CORE.y, R, 0, Math.PI * 2); ctx.clip();
            ctx.strokeStyle = 'rgba(210,235,255,0.45)'; ctx.lineWidth = 1.5;
            for (let j = 0; j < 7; j++) { ctx.beginPath(); ctx.ellipse(CORE.x, CORE.y, Math.abs(Math.cos(rot + j * 0.45)) * R, R, 0, 0, Math.PI * 2); ctx.stroke(); }
            for (let j = -3; j <= 3; j++) { ctx.beginPath(); ctx.ellipse(CORE.x, CORE.y + j * R / 3.6, R * 0.95, R * 0.18, 0, 0, Math.PI * 2); ctx.stroke(); }
            ctx.restore();
            // anéis giratórios
            ctx.lineWidth = 3;
            [[135, 1, 0.9], [168, -1.4, 0.6], [205, 0.7, 0.45]].forEach(([rad, sp, al], i) => {
              ctx.strokeStyle = `rgba(110,190,255,${al})`;
              ctx.setLineDash([60 - i * 14, 26 + i * 10]);
              ctx.lineDashOffset = -t * 90 * sp;
              ctx.beginPath(); ctx.ellipse(CORE.x, CORE.y, rad + pulse * 6, rad * 0.34 + pulse * 2, rot * sp * 0.5 + i, 0, Math.PI * 2); ctx.stroke();
            });
            ctx.setLineDash([]);
            // anel de progresso
            ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 8;
            ctx.beginPath(); ctx.arc(CORE.x, CORE.y, 222, 0, Math.PI * 2); ctx.stroke();
            ctx.strokeStyle = progress >= 1 ? C.blue : '#4DA6FF'; ctx.lineWidth = 8; ctx.lineCap = 'round';
            ctx.beginPath(); ctx.arc(CORE.x, CORE.y, 222, -Math.PI / 2, -Math.PI / 2 + progress * Math.PI * 2); ctx.stroke();
            ctx.lineCap = 'butt';
            ctx.font = `700 30px ${F.mono}`; ctx.textAlign = 'center';
            ctx.fillStyle = 'rgba(200,230,255,0.95)';
            ctx.fillText(`${Math.round(progress * 100)}%`, CORE.x, CORE.y + 175);
            ctx.textAlign = 'left';
            // órbita de partículas
            ctx.globalCompositeOperation = 'lighter';
            for (let j = 0; j < 36; j++) {
              const a = j * 0.7 + t * (0.8 + (j % 5) * 0.12);
              const rr = 110 + (j % 7) * 14;
              ctx.drawImage(glowSprite('rgba(150,210,255,0.9)', 32), CORE.x + Math.cos(a) * rr - 5, CORE.y + Math.sin(a) * rr * 0.4 - 5, 10, 10);
            }
          }}
        />
      </div>
      {/* HUD de texto */}
      <Hud t={t} />
    </div>
  );
};

const typed = (s: string, t: number, t0: number, cps = 32) => s.slice(0, Math.max(0, Math.floor((t - t0) * cps)));

const Hud: React.FC<{t: number}> = ({t}) => {
  const a1 = win(t, 3.35, 5.45, 0.2, 0.25);
  const a2 = win(t, 5.4, 7.3, 0.2, 0.3);
  const cursor = Math.floor(t * 3) % 2 === 0 ? '▌' : ' ';
  const style: React.CSSProperties = {position: 'absolute', left: 0, width: W, textAlign: 'center', fontFamily: F.mono, fontWeight: 700, fontSize: 46, letterSpacing: 3, color: C.white, textShadow: '0 0 24px rgba(8,126,255,0.9), 0 4px 20px #000'};
  return (
    <>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 520, background: 'linear-gradient(180deg, rgba(5,6,9,0.85), rgba(5,6,9,0))'}} />
      <div style={{...style, top: 345, opacity: a1}}>
        <span style={{color: '#7CC0FF'}}>&gt; </span>{typed('ANALISANDO PADRÃO VOCAL...', t, 3.4, 26)}{cursor}
      </div>
      <div style={{...style, top: 345, opacity: a2}}>
        <span style={{color: C.red}}>&gt; </span>{typed('RECONSTRUINDO VOZ...', t, 5.45, 26)}{cursor}
      </div>
      <div style={{position: 'absolute', left: 190, top: 415, width: 700, height: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 4, opacity: Math.max(a1, a2)}}>
        <div style={{width: `${clamp(map(t, 3.4, 7.0, 0, 1)) * 100}%`, height: '100%', borderRadius: 4, background: `linear-gradient(90deg, ${C.blue}, #7CC0FF)`, boxShadow: '0 0 16px #087EFF'}} />
      </div>
      <div style={{position: 'absolute', left: 190, top: 440, width: 700, display: 'flex', justifyContent: 'space-between', fontFamily: F.mono, fontSize: 21, color: 'rgba(160,205,255,0.75)', opacity: Math.max(a1, a2)}}>
        <span>FREQ {Math.round(180 + 60 * Math.sin(t * 3))}Hz</span><span>TIMBRE</span><span>ENTONAÇÃO</span><span>RITMO</span>
      </div>
    </>
  );
};
export const _s2 = [easeOut];
