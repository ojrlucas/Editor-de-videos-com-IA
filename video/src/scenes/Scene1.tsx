import React from 'react';
import {C, F, W, H} from '../theme';
import {BigText} from '../components/BigText';
import {PhoneBody, PhoneUI, PHONE_H, PHONE_W, wakeOn} from '../components/PhoneUI';
import {Canvas2D, glowSprite} from '../components/Canvas2D';
import {AmbientBG} from '../components/Overlays';
import {EV, clamp, easeInOut, easeOut, lerp, map, noise1, prog, rng, shakeAt, useG, win} from '../lib/time';

const bokeh = (() => {
  const r = rng(11);
  return Array.from({length: 26}, () => ({x: r() * W, y: r() * 1100, s: 50 + r() * 190, blue: r() > 0.4, a: 0.08 + r() * 0.2, ph: r() * 6}));
})();

const vibGate = (t: number) => {
  for (const v of EV.vibrate) if (t >= v && t < v + 0.4) return 1 - Math.pow((t - v) / 0.4, 4) * 0.4;
  return 0;
};

/** CENA 1 — O gancho (0–3s): celular vibrando na mesa, câmera avança, chamada, texto-choque. */
export const Scene1: React.FC = () => {
  const {t, f} = useG();
  const p = easeInOut(prog(t, 0, 2.3));
  const rx = lerp(66, 14, p);
  const tz = lerp(-250, 420, p);
  const ty = lerp(230, 150, p);
  const screenOn = wakeOn(t, 0.32);
  const red = clamp(map(t, 0.7, 2.2, 0, 1));
  const hit = shakeAt(t, [{at: EV.impact1, amp: 26}, ...EV.vibrate.map((v) => ({at: v, amp: 3, decay: 12}))]);
  const g = vibGate(t);
  const vx = Math.sin(t * 170) * 3.2 * g + noise1(t * 40) * 1.4 * g;
  const vy = Math.cos(t * 150) * 2.2 * g;
  const vr = Math.sin(t * 120) * 0.35 * g;
  const flash = clamp(1 - (t - EV.impact1) / 0.18) * (t >= EV.impact1 ? 1 : 0);
  const fade = win(t, 0, 99, 0.001, 0.0) * (1 - clamp(map(t, 3.0, 3.5, 0, 1)));
  const flick = screenOn * (0.85 + 0.15 * Math.sin(t * 38) * g + 0.15 * g);
  // objeto na mesa (xícara) ajuda a dar escala/profundidade
  return (
    <div style={{position: 'absolute', inset: 0, opacity: fade, transform: `translate(${hit.x}px,${hit.y}px) rotate(${hit.r}deg)`}}>
      <AmbientBG blue={0.28} red={red * 0.35} cx={50} cy={40} />
      {/* bokeh desfocado (profundidade de campo) */}
      <Canvas2D
        draw={(ctx) => {
          ctx.globalCompositeOperation = 'lighter';
          bokeh.forEach((b) => {
            const col = b.blue ? `rgba(8,126,255,${b.a})` : `rgba(255,38,61,${b.a * (0.3 + red)})`;
            const s = b.s * (1 + 0.04 * Math.sin(t * 1.5 + b.ph));
            ctx.globalAlpha = 1;
            ctx.drawImage(glowSprite(col, 128), b.x - s / 2, b.y - s / 2 - p * 40, s, s);
          });
        }}
      />
      {/* mundo 3D */}
      <div style={{position: 'absolute', inset: 0, perspective: 1250, perspectiveOrigin: '50% 52%'}}>
        <div style={{position: 'absolute', left: W / 2, top: H / 2, width: 0, height: 0, transformStyle: 'preserve-3d', transform: `translate3d(0px, ${ty}px, ${tz}px) rotateX(${rx}deg)`}}>
          {/* mesa */}
          <div
            style={{
              position: 'absolute', left: -3000, top: -9000, width: 6000, height: 12000,
              background: `
                radial-gradient(circle at 50% 75%, rgba(${60 + 195 * red * 0.0},${90 - 50 * red},${150 - 90 * red},0.55) 0%, rgba(8,20,40,0) 22%),
                repeating-linear-gradient(90deg, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.0) 3px, rgba(0,0,0,0.25) 14px, rgba(255,255,255,0.0) 40px),
                linear-gradient(180deg,#050609 0%,#07090e 18%,#0d1018 50%,#07080c)`,
            }}
          />
          {/* brilho da tela projetado na mesa */}
          <div style={{position: 'absolute', left: -700, top: -700, width: 1400, height: 1400, borderRadius: 700, opacity: flick * 0.9,
            background: `radial-gradient(circle, rgba(${Math.round(lerp(110, 255, red))},${Math.round(lerp(170, 60, red))},${Math.round(lerp(255, 80, red))},0.5) 0%, rgba(8,126,255,0.12) 38%, rgba(0,0,0,0) 62%)`}} />
          {/* celular deitado sobre a mesa */}
          <div style={{position: 'absolute', left: -PHONE_W / 2 + vx, top: -PHONE_H / 2 + vy, transform: `rotateZ(${-4 + vr}deg)`, transformStyle: 'preserve-3d'}}>
            <div style={{position: 'absolute', left: 14, top: 22, width: PHONE_W, height: PHONE_H, borderRadius: 60, background: 'rgba(0,0,0,0.75)', filter: 'blur(26px)'}} />
            <PhoneBody screenOn={flick} glare={0.7}>
              <PhoneUI lt={t - 0.32} mode="incoming" accent={red > 0.5 ? C.red : C.blue} />
            </PhoneBody>
          </div>
        </div>
      </div>
      {/* luz vermelha de alerta nas bordas */}
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 80% 60% at 50% 62%, rgba(255,38,61,0) 35%, rgba(255,38,61,${0.32 * red * (0.75 + 0.25 * Math.sin(t * 9))}) 100%)`, mixBlendMode: 'screen'}} />
      {/* gradiente superior p/ contraste do texto */}
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 820, background: 'linear-gradient(180deg, rgba(5,6,9,0.92) 0%, rgba(5,6,9,0.78) 45%, rgba(5,6,9,0) 100%)'}} />
      <BigText
        t0={0.28} t1={2.45} y={420} size={102} mode="rise" stagger={0.06} fadeOut={0.15}
        lines={[[{t: 'E SE SUA MÃE'}], [{t: 'TE LIGASSE PEDINDO'}], [{t: 'SOCORRO...', c: C.red}]]}
      />
      <BigText
        t0={EV.impact1} t1={3.75} y={420} size={118} mode="slam" stagger={0.1} fadeOut={0.4} glitch={t > EV.impact1 && t < EV.impact1 + 0.35 ? 1 : 0.12}
        lines={[[{t: '...MAS NÃO'}], [{t: 'FOSSE ELA?', c: C.red}]]}
      />
      <div style={{position: 'absolute', inset: 0, background: C.red, opacity: flash * 0.55, mixBlendMode: 'screen'}} />
    </div>
  );
};
export const _s1 = [F, easeOut];
