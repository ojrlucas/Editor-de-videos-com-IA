import React from 'react';
import {C, F, W, H} from '../theme';
import {Canvas2D, glowSprite} from '../components/Canvas2D';
import {BigText} from '../components/BigText';
import {EV, clamp, easeInOut, envAt, lerp, map, noise1, prog, rng, shakeAt, useG, win} from '../lib/time';

const dust = (() => {
  const r = rng(404);
  return Array.from({length: 90}, () => ({x: r() * W, y: r() * H, z: 0.2 + r() * 0.8, ph: r() * 6, red: r() > 0.5}));
})();

/** CENA 6 — O final (20–25s): quase preto, onda vermelha atravessa a tela, pergunta final legível até o último quadro. */
export const Scene6: React.FC = () => {
  const {t, f} = useG();
  const op = win(t, 19.92, 99, 0.2, 0.1);
  const sh = shakeAt(t, [{at: EV.finalHit, amp: 16}]);
  const zoom = lerp(1.0, 1.05, prog(t, 20, 25));
  const music = envAt('music', f);
  const head = lerp(-120, W + 140, easeInOut(prog(t, 20.0, 21.35)));
  const cyWave = lerp(980, 1215, easeInOut(prog(t, 21.2, 22.5)));
  const settle = clamp(map(t, 21.4, 22.4, 0, 1));
  const hitK = t >= EV.finalHit ? Math.exp(-(t - EV.finalHit) * 9) : 0;
  const titleShift = easeInOut(prog(t, 22.1, 22.7));

  return (
    <div style={{position: 'absolute', inset: 0, opacity: op}}>
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 70% 50% at 50% 55%, #0a0d18 0%, #050609 70%)'}} />
      <div style={{position: 'absolute', inset: 0, transform: `translate(${sh.x}px,${sh.y}px) scale(${zoom})`, transformOrigin: '50% 50%'}}>
        <Canvas2D
          draw={(ctx) => {
            ctx.globalCompositeOperation = 'lighter';
            dust.forEach((d) => {
              const px = (d.x + Math.sin(t * 0.3 + d.ph) * 20) % W;
              const py = (d.y - t * 8 * d.z + H * 4) % H;
              const s = 10 * d.z + 4;
              ctx.drawImage(glowSprite(d.red ? `rgba(255,60,80,${0.22 * d.z})` : `rgba(90,170,255,${0.2 * d.z})`, 32), px - s / 2, py - s / 2, s, s);
            });
            // onda sonora vermelha atravessando a tela
            const amp = lerp(150, 34 + 40 * music, settle) + hitK * 70;
            const pts: [number, number][] = [];
            for (let x = -10; x <= W + 10; x += 5) {
              if (x > head) break;
              const trail = clamp(1 - (head - x) / (settle > 0.99 ? 99999 : 650));
              const env = Math.sin(clamp((x + 100) / (W + 200)) * Math.PI) ** 0.6;
              const lead = clamp((head - x) / 220);
              const y = cyWave + (Math.sin(x * 0.03 - t * 11) * 0.65 + Math.sin(x * 0.071 + t * 7) * 0.35 + noise1(x * 0.02 + t) * 0.2) * amp * env * lead * (0.6 + 0.4 * Math.sin(x * 0.012 + 1.3));
              pts.push([x, y]);
              void trail;
            }
            if (pts.length > 1) {
              const al = lerp(1, 0.85, settle);
              [[34, 0.07], [18, 0.14], [8, 0.35], [3.2, 1]].forEach(([lw, a]) => {
                ctx.lineWidth = lw; ctx.lineJoin = 'round';
                ctx.strokeStyle = lw < 4 ? `rgba(255,170,180,${a * al})` : `rgba(255,38,61,${a * al})`;
                ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
              });
              // cabeça luminosa da onda
              const [hx, hy] = pts[pts.length - 1];
              if (head < W + 60) ctx.drawImage(glowSprite('rgba(255,90,110,1)', 128), hx - 120, hy - 120, 240, 240);
            }
            // anel de impacto final
            if (hitK > 0.02) {
              ctx.strokeStyle = `rgba(255,38,61,${hitK * 0.7})`; ctx.lineWidth = 6;
              ctx.beginPath(); ctx.arc(540, 900, 80 + (1 - hitK) * 700, 0, Math.PI * 2); ctx.stroke();
            }
          }}
        />
      </div>
      {/* gradiente suave atrás do texto p/ contraste */}
      <div style={{position: 'absolute', left: 0, top: 260, width: W, height: 900, background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(5,6,9,0.55), rgba(5,6,9,0))'}} />
      {/* texto 1 desce de importância e sobe quando o segundo surge */}
      <div style={{position: 'absolute', inset: 0, transform: `translateY(${-titleShift * 150}px) scale(${1 - titleShift * 0.22})`, transformOrigin: '50% 640px', opacity: 1 - titleShift * 0.18}}>
        <BigText
          t0={20.55} t1={99} y={620} size={124} mode="fade" stagger={0.24} fadeOut={0.01} spacing={3}
          glitch={hitK > 0.1 ? hitK * 0.5 : 0}
          lines={[[{t: 'SUA VOZ PODE'}], [{t: 'SER'}, {t: 'CLONADA.', c: C.red}]]}
        />
      </div>
      <BigText
        t0={22.2} t1={99} y={880} size={112} mode="rise" stagger={0.13} fadeOut={0.01} spacing={2}
        glitch={hitK > 0.1 ? hitK * 0.35 : 0}
        lines={[[{t: 'VOCÊ SABERIA'}], [{t: 'IDENTIFICAR UMA'}], [{t: 'LIGAÇÃO'}, {t: 'FALSA?', c: C.red}]]}
      />
    </div>
  );
};
export const _s6 = [F];
