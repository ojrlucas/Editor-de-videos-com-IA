import React, {useLayoutEffect, useRef} from 'react';
import {W, H, clamp, lerp, range, smooth, smoother} from './timeline';
import {HUDF} from './Fonts';

export const Vignette: React.FC<{amount?: number}> = ({amount = 0.8}) => (
  <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
    background: `radial-gradient(ellipse 75% 62% at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,3,14,${amount}) 100%)`}} />
);

/** Grão de filme animado (determinístico por frame). */
export const Grain: React.FC<{frame: number}> = ({frame}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const c = ref.current!; const ctx = c.getContext('2d')!;
    const img = ctx.createImageData(c.width, c.height);
    let s = (frame * 9301 + 49297) >>> 0;
    for (let i = 0; i < img.data.length; i += 4) {
      s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
      const v = (s >>> 24);
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  });
  return <canvas ref={ref} width={270} height={480} style={{position: 'absolute', inset: 0, width: '100%', height: '100%',
    mixBlendMode: 'overlay', opacity: 0.07, pointerEvents: 'none', imageRendering: 'pixelated'}} />;
};

/** Reflexo anamórfico horizontal + vazamento de luz (para relâmpagos e impactos). */
export const Flare: React.FC<{flash: number; t: number}> = ({flash, t}) => (
  <>
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'screen',
      background: `radial-gradient(ellipse 60% 40% at ${72 + 6 * Math.sin(t * 0.3)}% 8%, rgba(255,170,100,${0.10 + flash * 0.1}) 0%, rgba(255,150,80,0) 70%)`}} />
    {flash > 0.05 && (
      <div style={{position: 'absolute', left: 0, right: 0, top: `${30 + 20 * Math.sin(t * 40)}%`, height: 6, opacity: clamp(flash),
        mixBlendMode: 'screen', pointerEvents: 'none',
        background: 'linear-gradient(90deg, rgba(120,190,255,0), rgba(200,235,255,.95) 50%, rgba(120,190,255,0))', filter: 'blur(5px)'}} />
    )}
  </>
);

export const Flash: React.FC<{a: number; warm?: boolean}> = ({a, warm}) =>
  a > 0.005 ? <div style={{position: 'absolute', inset: 0, background: warm ? '#fff3df' : '#d8eeff', opacity: clamp(a), pointerEvents: 'none', mixBlendMode: 'screen'}} /> : null;

export const Disclaimer: React.FC<{a: number}> = ({a}) => (
  <div style={{position: 'absolute', left: 0, width: W, top: 1796, textAlign: 'center', fontFamily: HUDF, fontWeight: 600, fontSize: 25,
    letterSpacing: 1.5, color: 'rgba(200,225,255,0.62)', opacity: a, textTransform: 'uppercase'}}>
    Visualização artística baseada em modelos científicos · não é uma fotografia
  </div>
);
