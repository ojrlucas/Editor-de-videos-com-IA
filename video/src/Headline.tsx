import React from 'react';
import {W, clamp, easeOutBack, easeOutCubic, range, smooth} from './timeline';
import {HEAD} from './Fonts';

type Word = {text: string; hl?: boolean};
/** Título de impacto: palavras entram com escala/desfoque, brilho e tremor; saem suavemente. */
export const Headline: React.FC<{
  t: number; start: number; end: number | null; lines: Word[][]; size: number; y: number;
  style?: 'impact' | 'wind' | 'slow'; stagger?: number; fadeOut?: number;
}> = ({t, start, end, lines, size, y, style = 'impact', stagger = 0.11, fadeOut = 0.3}) => {
  if (t < start - 0.01 || (end !== null && t > end + 0.01)) return null;
  const lt = t - start;
  const out = end === null ? 1 : 1 - smooth(range(t, end - fadeOut, end));
  let idx = 0;
  return (
    <div style={{position: 'absolute', left: 0, width: W, top: y, transform: 'translateY(-50%)', textAlign: 'center',
      opacity: out, fontFamily: HEAD, fontWeight: 900, fontSize: size, lineHeight: 1.04, letterSpacing: -1,
      textTransform: 'uppercase'}}>
      {lines.map((ln, li) => (
        <div key={li} style={{display: 'flex', justifyContent: 'center', gap: size * 0.26, whiteSpace: 'nowrap'}}>
          {ln.map((w, wi) => {
            const k = idx++;
            const p = clamp((lt - k * stagger) / 0.42);
            const e = easeOutBack(p);
            const vis = p > 0;
            let tf = '', blur = 0;
            if (style === 'wind') {
              const dx = (1 - easeOutCubic(p)) * 520;
              tf = `translateX(${dx}px) skewX(${-(1 - easeOutCubic(p)) * 22}deg)`; blur = (1 - easeOutCubic(p)) * 26;
            } else if (style === 'slow') {
              tf = `scale(${1.08 - 0.08 * easeOutCubic(p)})`; blur = (1 - easeOutCubic(p)) * 14;
            } else {
              const sc = 1 + (1 - e) * 0.9;
              tf = `scale(${sc}) translateY(${(1 - easeOutCubic(p)) * 30}px)`; blur = (1 - easeOutCubic(p)) * 20;
            }
            const hit = Math.max(0, 1 - (lt - k * stagger) / 0.35);
            const col = w.hl
              ? 'linear-gradient(180deg,#ffffff 0%,#9be0ff 38%,#2d9bff 100%)'
              : 'linear-gradient(180deg,#ffffff 0%,#e8f4ff 60%,#bcdcff 100%)';
            return (
              <span key={wi} style={{
                opacity: vis ? clamp(p * 3) : 0, transform: tf, filter: `blur(${blur}px)`, display: 'inline-block',
                backgroundImage: col, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                WebkitTextFillColor: 'transparent',
                textShadow: 'none',
                filter2: undefined as any,
              } as React.CSSProperties}>
                <span style={{
                  display: 'inline-block',
                  filter: `drop-shadow(0 0 ${w.hl ? 26 : 16}px rgba(${w.hl ? '60,160,255' : '120,190,255'},${(w.hl ? 0.85 : 0.55) + hit * 0.4})) drop-shadow(0 6px 10px rgba(0,10,40,.75))`,
                }}>{w.text}</span>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};
