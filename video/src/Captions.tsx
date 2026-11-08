import React from 'react';
import {W, clamp, easeOutBack, range, smooth} from './timeline';
import {HEAD} from './Fonts';
import {TL} from './anim';

type Wd = {w: string; hl: number; s: number; e: number};
type Chunk = {words: Wd[]; start: number; end: number};

// Agrupa palavras em blocos de no máximo 2 linhas (≈ 24 caracteres), quebrando em pontuação.
const build = (): Chunk[] => {
  const out: Chunk[] = [];
  for (const s of TL.sentences) {
    if (s.i === 5) continue; // a pergunta final é exibida como título em destaque
    let cur: Wd[] = [];
    const flush = () => { if (cur.length) { out.push({words: cur, start: cur[0].s, end: cur[cur.length - 1].e}); cur = []; } };
    s.words.forEach((w, k) => {
      const len = [...cur, w].map((x) => x.w).join(' ').length;
      if (cur.length && (len > 24 || cur.length >= 4)) flush();
      cur.push(w);
      if (/[,.!?]$/.test(w.w)) flush();
    });
    flush();
  }
  return out;
};
const CHUNKS = build();

export const Captions: React.FC<{t: number}> = ({t}) => {
  const ch = CHUNKS.find((c, i) => {
    const next = CHUNKS[i + 1];
    const endShow = Math.min(c.end + 0.18, next ? next.start : 99);
    return t >= c.start - 0.04 && t < endShow;
  });
  if (!ch) return null;
  const lt = t - ch.start;
  const inP = easeOutBack(clamp((lt + 0.04) / 0.2));
  const outP = 1 - smooth(range(t, ch.end + 0.08, ch.end + 0.18));
  return (
    <div style={{position: 'absolute', left: 70, width: W - 140, top: 1432, height: 240, display: 'flex', alignItems: 'center',
      justifyContent: 'center', opacity: Math.min(1, clamp(inP * 3)) * outP, transform: `translateY(${(1 - inP) * 26}px) scale(${0.94 + 0.06 * inP})`}}>
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: 22, rowGap: 6,
        fontFamily: HEAD, fontWeight: 900, fontSize: 74, lineHeight: 1.08, textTransform: 'uppercase', letterSpacing: -0.5}}>
        {ch.words.map((w, i) => {
          const active = t >= w.s && t < w.e;
          const spoken = t >= w.s;
          const pop = active ? 1 + 0.13 * Math.sin(clamp((t - w.s) / 0.16) * Math.PI) + 0.04 : 1;
          const blue = w.hl === 1;
          const color = blue ? '#4fb6ff' : '#ffffff';
          return (
            <span key={i} style={{
              display: 'inline-block', transform: `scale(${pop})`, color: spoken ? color : 'rgba(255,255,255,0.45)',
              WebkitTextStroke: '3px rgba(2,12,40,.92)', paintOrder: 'stroke fill',
              textShadow: blue && spoken
                ? '0 0 28px rgba(60,160,255,.95), 0 0 60px rgba(40,120,255,.7), 0 6px 14px rgba(0,8,30,.9)'
                : '0 0 18px rgba(150,205,255,.45), 0 6px 14px rgba(0,8,30,.9)',
              opacity: spoken ? 1 : 0.55,
            }}>{w.w}</span>
          );
        })}
      </div>
    </div>
  );
};
