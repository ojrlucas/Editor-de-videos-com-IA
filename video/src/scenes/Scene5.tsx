import React from 'react';
import {C, F, W, H} from '../theme';
import {Canvas2D, glowSprite} from '../components/Canvas2D';
import {AmbientBG} from '../components/Overlays';
import {BigText} from '../components/BigText';
import {PhoneUI} from '../components/PhoneUI';
import {drawSilhouettePaths, getSilhouette} from '../lib/silhouette';
import {EV, clamp, easeInOut, easeOut, envAt, lerp, map, noise1, prog, rng, shakeAt, useG, voiceAmp, win} from '../lib/time';

const T0 = EV.reveal;
const FREEZE = EV.silenceStart;
const specCols = (() => {
  const r = rng(31);
  return Array.from({length: 96}, () => Array.from({length: 14}, () => r()));
})();

const typed = (s: string, t: number, t0: number, cps = 30) => s.slice(0, Math.max(0, Math.floor((t - t0) * cps)));

const Panel: React.FC<{x: number; y: number; w: number; h: number; title?: string; right?: React.ReactNode; children?: React.ReactNode; glow?: number}> = ({x, y, w, h, title, right, children, glow = 0.35}) => (
  <div style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: 18, background: 'linear-gradient(180deg, rgba(9,18,38,0.96), rgba(5,9,20,0.98))', border: '2px solid rgba(70,150,255,0.55)', boxShadow: `0 0 60px rgba(8,126,255,${glow}), inset 0 0 40px rgba(8,126,255,0.1)`, overflow: 'hidden'}}>
    {title && (
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 46, padding: '0 20px', borderBottom: '1px solid rgba(70,150,255,0.35)', fontFamily: F.mono, fontSize: 21, fontWeight: 700, letterSpacing: 2, color: 'rgba(150,205,255,0.95)'}}>
        <span>{title}</span><span>{right}</span>
      </div>
    )}
    {children}
  </div>
);

/** CENA 5 — A revelação (16–20s): glitch brusco, interface de IA simulando a voz, câmera recua. */
export const Scene5: React.FC = () => {
  const {t, f} = useG();
  const pts = getSilhouette();
  const pull = easeOut(prog(t, 16.12, 19.0));
  const scale = lerp(3.6, 1.0, pull);
  const rot = lerp(3.5, 0, pull);
  const frozen = t >= FREEZE;
  const live = clamp(1 - map(t, FREEZE, FREEZE + 0.25, 0, 1));
  const dim = 1 - 0.78 * clamp(map(t, 19.1, 19.9, 0, 1));
  const sh = shakeAt(t, [{at: EV.reveal, amp: 34}, {at: EV.textArtificial, amp: 12}]);
  const op = win(t, T0, 20.4, 0.001, 0.001);
  const glitchCall = t < 16.95; // fragmentos da voz da ligação sendo "desfeitos"
  const amp = glitchCall ? Math.max(0.35, envAt('sfx', f)) : voiceAmp(t) * live;
  const callSec = 5 + (t - 16);
  const gl = glitchCall ? 1 : 0;

  return (
    <div style={{position: 'absolute', inset: 0, opacity: op * dim}}>
      <AmbientBG blue={0.3} red={0.06} cx={50} cy={50} />
      <div style={{position: 'absolute', inset: 0, transform: `translate(${sh.x}px,${sh.y}px) rotate(${rot}deg) scale(${scale})`, transformOrigin: '50% 45%'}}>
        <Canvas2D
          draw={(ctx) => {
            // fundo: grade e partículas
            ctx.strokeStyle = 'rgba(8,126,255,0.1)'; ctx.lineWidth = 1;
            for (let x = 0; x <= W; x += 60) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
            for (let y = 0; y <= H; y += 60) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
          }}
        />
        {/* monitor principal */}
        <Panel x={70} y={560} w={940} h={590} title="SÍNTESE DE VOZ  ·  MODELO GENERATIVO" right={<span style={{color: frozen ? '#8aa' : C.red, opacity: frozen ? 0.8 : 0.5 + 0.5 * Math.sin(t * 8)}}>{frozen ? '■ PAUSADO' : '● AO VIVO'}</span>} glow={0.5}>
          <div />
        </Panel>
        <Canvas2D
          draw={(ctx) => {
            // silhueta digital fantasma atrás da onda
            ctx.globalCompositeOperation = 'lighter';
            const S = 0.62, ox = 540, oy = 880;
            pts.forEach((p, i) => {
              if (i % 2) return;
              const x = ox + (p.x - 540) * S, y = oy + (p.y - 1000) * S;
              if (y < 612 || y > 1090) return;
              const a = (p.part === 1 ? 0.55 : 0.3) * (0.7 + 0.3 * Math.sin(t * 5 + p.r1 * 30)) * (0.5 + 0.5 * live);
              ctx.fillStyle = `rgba(${p.part === 1 ? '140,210,255' : '30,120,255'},${a})`;
              ctx.fillRect(x, y, 2.6, 2.6);
            });
            ctx.globalCompositeOperation = 'source-over';
            // onda de voz principal (reativa ao áudio) com glitches nos primeiros instantes
            const x0 = 100, x1 = 980, cy = 790;
            const draw = (lw: number, col: string, off: number) => {
              ctx.lineWidth = lw; ctx.strokeStyle = col; ctx.beginPath();
              for (let x = x0; x <= x1; x += 4) {
                const e = Math.sin(((x - x0) / (x1 - x0)) * Math.PI) ** 0.8;
                let y = Math.sin(x * 0.045 + t * 14) * 70 * amp * e + Math.sin(x * 0.11 - t * 9) * 38 * amp * e + noise1(x * 0.03 + t * 3) * 10 * (0.3 + amp) * e;
                if (glitchCall && Math.sin(x * 0.05 + f * 3.7) > 0.55) y *= -1.8;
                y += off;
                x === x0 ? ctx.moveTo(x, cy + y) : ctx.lineTo(x, cy + y);
              }
              ctx.stroke();
            };
            ctx.globalCompositeOperation = 'lighter';
            draw(16, 'rgba(8,126,255,0.14)', 0);
            draw(7, 'rgba(8,126,255,0.35)', 0);
            draw(3, glitchCall && f % 4 < 2 ? 'rgba(255,90,110,1)' : 'rgba(210,235,255,1)', 0);
            if (glitchCall) draw(3, 'rgba(255,38,61,0.8)', 14);
            ctx.globalCompositeOperation = 'source-over';
            ctx.fillStyle = 'rgba(70,150,255,0.45)'; ctx.fillRect(x0, cy, x1 - x0, 1.5);
            // espectrograma rolando
            const sy0 = 925, hh = 70, cols = 96;
            for (let c = 0; c < cols; c++) {
              const colData = specCols[(c + Math.floor(frozen ? FREEZE * 12 : t * 12)) % cols];
              for (let r = 0; r < 14; r++) {
                const v = colData[r] * (1 - r / 18) * (0.4 + amp * 0.9);
                ctx.fillStyle = `rgba(${Math.round(30 + 200 * v)},${Math.round(110 + 110 * v)},255,${0.15 + v * 0.85})`;
                ctx.fillRect(100 + c * 9.2, sy0 + hh - (r + 1) * 5, 8, 4.2);
              }
            }
            // indicadores de processamento
            const bars: [string, number, string][] = [['ANÁLISE', 1, C.blue], ['CLONAGEM', clamp(map(t, 16.2, 17.4, 0.4, 1)), C.blue], ['SÍNTESE', frozen ? 1 : 0.55 + 0.45 * Math.abs(Math.sin(t * 2.1)), C.red]];
            bars.forEach(([label, v, col], i) => {
              const bx = 100 + i * 295, by = 1050;
              ctx.font = `700 20px ${F.mono}`; ctx.fillStyle = 'rgba(160,205,255,0.9)'; ctx.fillText(label, bx, by - 12);
              ctx.textAlign = 'right'; ctx.fillText(`${Math.round(v * 100)}%`, bx + 270, by - 12); ctx.textAlign = 'left';
              ctx.fillStyle = 'rgba(255,255,255,0.12)'; ctx.fillRect(bx, by, 270, 10);
              ctx.fillStyle = col; ctx.fillRect(bx, by, 270 * v, 10);
              ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = col === C.red ? 'rgba(255,38,61,0.35)' : 'rgba(8,126,255,0.35)'; ctx.fillRect(bx, by - 3, 270 * v, 16); ctx.globalCompositeOperation = 'source-over';
            });
          }}
        />
        {/* monitor esquerdo: ligação simulada */}
        <Panel x={70} y={1175} w={440} h={150} title="CHAMADA" right={<span style={{color: C.red}}>SIMULADA</span>}>
          <div style={{position: 'absolute', left: 0, top: 46, width: 440, height: 104, display: 'flex', alignItems: 'center', gap: 18, padding: '0 20px', boxSizing: 'border-box'}}>
            <div style={{width: 64, height: 64, borderRadius: 32, background: 'linear-gradient(145deg,#2a3a63,#101830)', border: '2px solid rgba(255,255,255,0.2)', overflow: 'hidden', flexShrink: 0}}>
              <svg width="64" height="64" viewBox="0 0 128 128"><circle cx="64" cy="50" r="22" fill="rgba(255,255,255,0.78)" /><path d="M18 128c2-34 22-48 46-48s44 14 46 48z" fill="rgba(255,255,255,0.78)" /></svg>
            </div>
            <div style={{fontFamily: F.body, color: '#fff'}}>
              <div style={{fontSize: 30, fontWeight: 700}}>Mãe</div>
              <div style={{fontFamily: F.mono, fontSize: 20, color: 'rgba(170,210,255,0.85)'}}>00:{String(Math.floor(callSec)).padStart(2, '0')} · voz sintética</div>
            </div>
            <div style={{display: 'flex', gap: 4, marginLeft: 'auto', alignItems: 'center'}}>
              {Array.from({length: 7}, (_, i) => <div key={i} style={{width: 5, height: 8 + 40 * amp * (0.5 + 0.5 * Math.sin(t * 13 + i * 1.7)), background: C.blue, borderRadius: 3}} />)}
            </div>
          </div>
        </Panel>
        {/* monitor direito: texto → voz */}
        <Panel x={540} y={1175} w={470} h={150} title="TEXTO → VOZ" right={<span style={{color: '#7CC0FF'}}>SAÍDA</span>}>
          <div style={{padding: '12px 20px', fontFamily: F.mono, fontSize: 21, lineHeight: 1.45, color: 'rgba(190,225,255,0.95)'}}>
            <div style={{color: 'rgba(120,170,230,0.8)'}}>&gt; entrada: texto</div>
            <div>"{typed('Filho... preciso da sua ajuda...', t, 16.4, 34)}<span style={{opacity: Math.floor(t * 4) % 2 ? 0 : 1}}>▌</span>"</div>
            <div style={{color: frozen ? '#9ab' : C.red}}>&gt; saída: áudio {frozen ? 'concluído' : 'sintético'}</div>
          </div>
        </Panel>
        {/* nome do modelo e tags flutuantes ao redor (aparecem com o recuo) */}
        <div style={{position: 'absolute', left: 70, top: 1355, fontFamily: F.mono, fontSize: 20, letterSpacing: 2, color: 'rgba(120,170,230,0.0)'}} />
      </div>
      {/* gradiente do topo p/ contraste do texto */}
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 640, background: 'linear-gradient(180deg, rgba(5,6,9,0.92), rgba(5,6,9,0.6) 60%, rgba(5,6,9,0))'}} />
      <BigText
        t0={EV.textArtificial} t1={19.55} y={400} size={122} mode="slam" stagger={0.14} fadeOut={0.4}
        glitch={t < EV.textArtificial + 0.5 ? 1 : frozen ? 0.5 : 0.12}
        lines={[[{t: 'A VOZ ERA'}], [{t: 'ARTIFICIAL.', c: C.red}]]}
      />
    </div>
  );
};
export const _s5 = [drawSilhouettePaths, glowSprite, easeInOut, lerp, PhoneUI];
