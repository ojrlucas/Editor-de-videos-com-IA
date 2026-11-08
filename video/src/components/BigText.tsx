import React from 'react';
import {C, F, W} from '../theme';
import {clamp, easeOut, easeOutBack, rng, useG} from '../lib/time';

export type Seg = {t: string; c?: string};
type Mode = 'slam' | 'rise' | 'fade';

/**
 * Texto principal grande (Anton) com animação por palavra.
 * lines: linhas → trechos coloridos. Visível em [t0,t1]. y = centro vertical do bloco.
 */
export const BigText: React.FC<{
  lines: Seg[][];
  t0: number;
  t1: number;
  y: number;
  size?: number;
  mode?: Mode;
  stagger?: number;
  fadeOut?: number;
  glitch?: number; // 0..1 deslocamento cromático do texto
  color?: string;
  spacing?: number;
  lineHeight?: number;
}> = ({lines, t0, t1, y, size = 104, mode = 'rise', stagger = 0.07, fadeOut = 0.25, glitch = 0, color = C.white, spacing = 2, lineHeight = 1.04}) => {
  const {t, f} = useG();
  if (t < t0 - 0.02 || t > t1 + 0.02) return null;
  const outK = clamp((t1 - t) / fadeOut);
  let wi = 0;
  const r = rng(f * 13 + 1);
  return (
    <div
      style={{
        position: 'absolute', left: 0, width: W, top: y, transform: 'translateY(-50%)', textAlign: 'center',
        fontFamily: F.display, fontSize: size, lineHeight, letterSpacing: spacing, textTransform: 'uppercase',
        opacity: outK, padding: '0 60px', boxSizing: 'border-box',
      }}
    >
      {lines.map((line, li) => (
        <div key={li} style={{whiteSpace: 'nowrap'}}>
          {line.map((seg, si) =>
            seg.t.split(' ').filter(Boolean).map((w, k) => {
              const i = wi++;
              const p = clamp((t - t0 - i * stagger) / (mode === 'slam' ? 0.22 : 0.4));
              const col = seg.c ?? color;
              const isRed = col === C.red;
              let tr = '';
              let op = 1;
              let blur = 0;
              if (mode === 'slam') {
                const e = easeOutBack(p);
                tr = `scale(${1 + (1 - e) * 0.9})`;
                op = clamp(p * 3);
                blur = (1 - p) * 14;
              } else if (mode === 'rise') {
                tr = `translateY(${(1 - easeOut(p)) * 36}px)`;
                op = easeOut(p);
                blur = (1 - p) * 8;
              } else op = p;
              const g = glitch * (0.4 + r());
              return (
                <span
                  key={`${si}-${k}`}
                  style={{
                    display: 'inline-block', marginRight: '0.28em', opacity: op, transform: tr, filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
                    color: col,
                    textShadow: [
                      '0 6px 40px rgba(0,0,0,0.9)',
                      isRed ? '0 0 36px rgba(255,38,61,0.65)' : col === C.blue ? '0 0 36px rgba(8,126,255,0.7)' : '0 0 24px rgba(255,255,255,0.18)',
                      glitch > 0.02 ? `${6 * g}px 0 rgba(255,38,61,0.8), ${-6 * g}px 0 rgba(8,126,255,0.8)` : '',
                    ].filter(Boolean).join(', '),
                  }}
                >
                  {w}
                </span>
              );
            }),
          )}
        </div>
      ))}
    </div>
  );
};
