import React from 'react';
import {rng} from '../lib/time';

/** Definições SVG (isolam canais de cor para aberração cromática) */
export const GlitchDefs: React.FC = () => (
  <svg width={0} height={0} style={{position: 'absolute'}}>
    <defs>
      <filter id="chR" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" />
      </filter>
      <filter id="chB" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" />
      </filter>
      <filter id="chG" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" />
      </filter>
    </defs>
  </svg>
);

/**
 * Glitch controlado: aberração cromática RGB + fatias horizontais deslocadas.
 * intensity 0 = desligado (renderiza só os filhos, sem custo extra).
 */
export const GlitchWrap: React.FC<{intensity: number; f: number; seed?: number; slices?: number; children: React.ReactNode}> = ({intensity, f, seed = 0, slices = 5, children}) => {
  if (intensity < 0.02) return <>{children}</>;
  const r = rng(f * 131 + seed * 17 + 5);
  const split = 6 + intensity * 38;
  const full: React.CSSProperties = {position: 'absolute', inset: 0};
  const sl = Array.from({length: Math.round(slices * (0.5 + intensity))}, () => {
    const top = r() * 92;
    const h = 1.5 + r() * 9 * intensity + 1;
    return {top, h, dx: (r() - 0.5) * 240 * intensity, k: r()};
  });
  return (
    <div style={{position: 'absolute', inset: 0}}>
      <div style={full}>{children}</div>
      <div style={{...full, filter: 'url(#chR)', mixBlendMode: 'screen', transform: `translateX(${split * (r() > 0.5 ? 1 : -1)}px)`}}>{children}</div>
      <div style={{...full, filter: 'url(#chB)', mixBlendMode: 'screen', transform: `translateX(${-split}px)`}}>{children}</div>
      {sl.map((s, i) => (
        <div key={i} style={{...full, clipPath: `inset(${s.top}% 0 ${Math.max(0, 100 - s.top - s.h)}% 0)`, transform: `translateX(${s.dx}px)`}}>
          {children}
        </div>
      ))}
    </div>
  );
};

/** Barras luminosas de glitch (overlay barato, sem duplicar filhos) */
export const GlitchBars: React.FC<{intensity: number; f: number; seed?: number}> = ({intensity, f, seed = 0}) => {
  if (intensity < 0.02) return null;
  const r = rng(f * 977 + seed);
  const n = Math.round(4 + intensity * 12);
  return (
    <div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', pointerEvents: 'none'}}>
      {Array.from({length: n}, (_, i) => {
        const w = 120 + r() * 800;
        const color = r() > 0.5 ? 'rgba(255,38,61,0.55)' : r() > 0.4 ? 'rgba(8,126,255,0.6)' : 'rgba(245,245,245,0.5)';
        return <div key={i} style={{position: 'absolute', left: r() * (1080 - w), top: r() * 1900, width: w, height: 2 + r() * 14 * intensity, background: color}} />;
      })}
    </div>
  );
};
