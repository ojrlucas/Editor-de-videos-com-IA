import React from 'react';
import {C, F, W, H} from '../theme';
import {Canvas2D, glowSprite} from '../components/Canvas2D';
import {AmbientBG} from '../components/Overlays';
import {BigText} from '../components/BigText';
import {FACE, drawFaceMesh, drawSilhouettePaths, getSilhouette} from '../lib/silhouette';
import {EV, clamp, easeInOut, easeOut, lerp, map, noise1, prog, rng, useG, voiceAmp, win} from '../lib/time';

const T0 = 7.0;

/** CENA 3 — Reconstrução (7–11s): silhueta feminina surge de partículas; escaneamento facial; zoom lento. */
export const Scene3: React.FC = () => {
  const {t, f} = useG();
  const pts = getSilhouette();
  const cam = easeInOut(prog(t, T0, 11.3));
  const scale = lerp(1.0, 1.2, cam);
  const camY = lerp(70, 30, cam);
  const op = win(t, T0, 11.6, 0.001, 0.001);
  const scanY = lerp(700, 1060, (Math.sin(t * 2.4) * 0.5 + 0.5));
  const assemble = (p: {y: number; r1: number}) => clamp((t - 7.15 - ((p.y - 650) / 1000) * 1.9 - p.r1 * 0.7) / 0.9);
  const pct = Math.round(clamp(map(t, 7.2, 10.8, 0, 1)) * 100);

  return (
    <div style={{position: 'absolute', inset: 0, opacity: op}}>
      <AmbientBG blue={0.26} red={0.05 + 0.04 * Math.sin(t * 5)} cx={50} cy={52} />
      <div style={{position: 'absolute', inset: 0, transform: `translateY(${camY}px) scale(${scale})`, transformOrigin: '50% 55%'}}>
        <Canvas2D
          draw={(ctx) => {
            // halo atrás da silhueta
            ctx.globalCompositeOperation = 'lighter';
            ctx.drawImage(glowSprite('rgba(8,126,255,0.45)', 128), 540 - 620, 1000 - 620, 1240, 1240);
            // nuvem de partículas formando a silhueta
            const swirl = (p: {x: number; y: number; r1: number; r2: number; r3: number}, k: number) => {
              const a = p.r2 * Math.PI * 2 + t * 0.7 * (0.5 + p.r3);
              const rad = (1 - k) * (300 + p.r3 * 700);
              return {x: p.x + Math.cos(a) * rad, y: p.y + Math.sin(a) * rad * 0.7 - (1 - k) * 160};
            };
            pts.forEach((p) => {
              const k = easeOut(assemble(p));
              if (k <= 0) return;
              const q = swirl(p, k);
              const shimmer = 0.75 + 0.25 * Math.sin(t * 6 + p.r1 * 40);
              // metade direita do rosto se dissolve (rosto parcialmente visível)
              const fx = (p.x - FACE.cx) / FACE.rx, fy = (p.y - FACE.cy) / FACE.ry;
              const inFace = p.part === 1;
              let alpha = k * shimmer;
              if (inFace && fx > 0.05) alpha *= clamp(1 - fx * 0.9 + (p.r2 - 0.5) * 0.5 - 0.25 * Math.sin(t * 3 + p.r3 * 9));
              if (p.y > 1480) alpha *= clamp((1620 - p.y) / 140);
              const size = inFace ? 4.4 : p.part === 0 ? 3.6 : 3.4;
              let r = 8, g = 126, b = 255;
              if (inFace) { r = 120; g = 200; b = 255; }
              if (p.part === 0) { r = 8; g = 90; b = 230; }
              // faixa varrida pelo scanner fica brilhante
              const near = Math.exp(-Math.pow((p.y - scanY) / 26, 2));
              if (near > 0.1) { r = lerp(r, 255, near); g = lerp(g, 255, near); b = 255; alpha = Math.min(1, alpha + near * 0.6); }
              if (k < 0.98) { ctx.fillStyle = `rgba(200,230,255,${alpha * 0.9})`; } else { ctx.fillStyle = `rgba(${r | 0},${g | 0},${b | 0},${alpha})`; }
              ctx.fillRect(q.x - size / 2, q.y - size / 2, size, size);
            });
            ctx.globalCompositeOperation = 'source-over';
            // rosto: malha de escaneamento + olhos
            const meshA = clamp(map(t, 8.0, 8.8, 0, 1)) * 0.75;
            if (meshA > 0) {
              ctx.save();
              ctx.beginPath(); ctx.ellipse(FACE.cx, FACE.cy, FACE.rx, FACE.ry, 0, 0, Math.PI * 2); ctx.clip();
              // aplica a máscara apenas na metade esquerda + transição
              const mask = ctx.createLinearGradient(FACE.cx - 20, 0, FACE.cx + 90, 0);
              mask.addColorStop(0, 'rgba(0,0,0,1)'); mask.addColorStop(1, 'rgba(0,0,0,0)');
              ctx.globalCompositeOperation = 'lighter';
              drawFaceMesh(ctx, meshA, t * 0.8, scanY);
              ctx.restore();
              // olhos brilhando
              ctx.globalCompositeOperation = 'lighter';
              const ea = clamp(map(t, 8.4, 9.0, 0, 1));
              [[497, 868, 1], [583, 868, 0.35]].forEach(([x, y, a]) => {
                ctx.drawImage(glowSprite(`rgba(160,220,255,${a * ea})`, 64), x - 26, y - 14, 52, 28);
              });
              ctx.globalCompositeOperation = 'source-over';
            }
            // linha de scan horizontal
            const sa = clamp(map(t, 7.4, 7.9, 0, 1));
            ctx.globalCompositeOperation = 'lighter';
            const sg = ctx.createLinearGradient(0, scanY - 30, 0, scanY + 30);
            sg.addColorStop(0, 'rgba(8,126,255,0)'); sg.addColorStop(0.5, `rgba(150,215,255,${0.85 * sa})`); sg.addColorStop(1, 'rgba(8,126,255,0)');
            ctx.fillStyle = sg; ctx.fillRect(150, scanY - 30, 780, 60);
            ctx.globalCompositeOperation = 'source-over';
            // colchetes de enquadramento do rosto
            const ba = clamp(map(t, 8.2, 8.7, 0, 1));
            ctx.strokeStyle = `rgba(150,215,255,${0.9 * ba})`; ctx.lineWidth = 4;
            const bx0 = FACE.cx - 190, bx1 = FACE.cx + 190, by0 = FACE.cy - 215, by1 = FACE.cy + 215, L = 54;
            [[bx0, by0, 1, 1], [bx1, by0, -1, 1], [bx0, by1, 1, -1], [bx1, by1, -1, -1]].forEach(([x, y, dx, dy]) => {
              ctx.beginPath(); ctx.moveTo(x, y + dy * L); ctx.lineTo(x, y); ctx.lineTo(x + dx * L, y); ctx.stroke();
            });
            ctx.font = `700 24px ${F.mono}`; ctx.fillStyle = `rgba(150,215,255,${ba})`;
            ctx.fillText(`ESCANEANDO  ${pct}%`, bx0, by0 - 18);
            ctx.textAlign = 'right';
            ctx.fillStyle = `rgba(255,80,100,${ba * (0.6 + 0.4 * Math.sin(t * 9))})`;
            ctx.fillText('● VOZ', bx1, by0 - 18);
            ctx.textAlign = 'left';
            // linha de onda de voz atravessando o busto (reação ao áudio)
            const wa = clamp(map(t, 7.6, 8.2, 0, 1));
            ctx.strokeStyle = `rgba(120,200,255,${0.8 * wa})`; ctx.lineWidth = 3;
            ctx.beginPath();
            for (let x = 120; x <= 960; x += 6) {
              const env = Math.sin(((x - 120) / 840) * Math.PI);
              const y = 1500 + Math.sin(x * 0.04 + t * 12) * 34 * env * (0.2 + voiceAmp(t)) + noise1(x * 0.02 + t) * 6 * env;
              x === 120 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }
            ctx.stroke();
          }}
        />
      </div>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 700, background: 'linear-gradient(180deg, rgba(5,6,9,0.9), rgba(5,6,9,0.55) 55%, rgba(5,6,9,0))'}} />
      <BigText
        t0={7.55} t1={9.5} y={400} size={90} mode="rise" stagger={0.09} fadeOut={0.25}
        lines={[[{t: 'APENAS ALGUNS'}], [{t: 'SEGUNDOS DE'}, {t: 'ÁUDIO...', c: '#5DB0FF'}]]}
      />
      <BigText
        t0={9.55} t1={11.2} y={400} size={90} mode="slam" stagger={0.08} fadeOut={0.2}
        lines={[[{t: '...PODEM SER'}], [{t: 'SUFICIENTES PARA'}], [{t: 'UM GOLPE.', c: C.red}]]}
      />
    </div>
  );
};
export const _s3 = [drawSilhouettePaths, EV, rng, H];
