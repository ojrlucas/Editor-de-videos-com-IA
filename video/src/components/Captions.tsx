import React from 'react';
import captionsData from '../generated/captions.json';
import {C, F, W} from '../theme';
import {clamp, easeOut, useG} from '../lib/time';

type Word = {w: string; s: number; e: number};
type Phrase = {id: string; start: number; end: number; words: Word[]; kind: string};

const norm = (w: string) => w.toLowerCase().replace(/[^a-záàâãéêíóôõúüç]/g, '');
const RED = new Set(['socorro', 'clonada', 'falsa', 'golpe', 'artificial_r']);
const BLUE = new Set(['inteligência', 'artificial']);

/** divide a fala em "páginas" de no máximo 2 linhas curtas */
const pages: {words: Word[]; id: string; kind: string; start: number; end: number}[] = [];
(captionsData as Phrase[]).forEach((p) => {
  let cur: Word[] = [];
  let chars = 0;
  const flush = () => {
    if (cur.length) pages.push({words: cur, id: p.id, kind: p.kind, start: cur[0].s, end: cur[cur.length - 1].e});
    cur = [];
    chars = 0;
  };
  p.words.forEach((w) => {
    if (cur.length && (chars + w.w.length > 26 || cur.length >= 5)) flush();
    cur.push(w);
    chars += w.w.length + 1;
  });
  flush();
});

const colorFor = (word: string, pageId: string) => {
  const n = norm(word);
  if (n === 'artificial' && pageId === 'n5') return C.red;
  if (RED.has(n)) return C.red;
  if (BLUE.has(n)) return '#3D9BFF';
  return C.white;
};

/** Legendas dinâmicas: região central-inferior, máx. 2 linhas, palavra atual em destaque. */
export const Captions: React.FC = () => {
  const {t} = useG();
  const idx = pages.findIndex((p, i) => {
    const next = pages[i + 1];
    const end = p.end + (next && next.start - p.end < 0.4 ? (next.start - p.end) * 0.5 : 0.28);
    return t >= p.start - 0.05 && t < end;
  });
  if (idx < 0) return null;
  const p = pages[idx];
  const inK = easeOut((t - (p.start - 0.05)) / 0.16);
  const isCall = p.kind === 'call';
  const outK = clamp((p.end + 0.28 - t) / 0.12);
  return (
    <div
      style={{
        position: 'absolute', left: 0, width: W, top: 1328, display: 'flex', justifyContent: 'center',
        opacity: inK * Math.min(1, outK), transform: `translateY(${(1 - inK) * 22}px)`,
      }}
    >
      <div
        style={{
          width: 880, textAlign: 'center', fontFamily: F.body, fontWeight: 800, fontSize: 62, lineHeight: 1.12,
          textTransform: 'uppercase', letterSpacing: -0.5, fontStyle: isCall ? 'italic' : 'normal',
        }}
      >
        {isCall && (
          <div style={{fontFamily: F.mono, fontSize: 24, fontWeight: 700, letterSpacing: 5, color: '#7CB8FF', marginBottom: 10, fontStyle: 'normal'}}>
            ◉ VOZ DA LIGAÇÃO
          </div>
        )}
        {p.words.map((w, i) => {
          const active = t >= w.s && t < w.e;
          const spoken = t >= w.s;
          const col = colorFor(w.w, p.id);
          const colored = col !== C.white;
          const k = clamp((t - w.s) / 0.12);
          return (
            <span
              key={i}
              style={{
                display: 'inline-block', marginRight: '0.36em',
                color: spoken ? col : 'rgba(245,245,245,0.38)',
                transform: `scale(${active ? 1 + 0.07 * (1 - k * 0.4) : 1})`,
                textShadow: [
                  '0 3px 0 rgba(0,0,0,0.9)', '0 0 14px rgba(0,0,0,0.95)', '0 6px 34px rgba(0,0,0,0.9)',
                  spoken && colored ? `0 0 26px ${col === C.red ? 'rgba(255,38,61,0.7)' : 'rgba(8,126,255,0.75)'}` : '',
                ].filter(Boolean).join(', '),
                WebkitTextStroke: '2px rgba(0,0,0,0.55)',
                paintOrder: 'stroke fill',
              }}
            >
              {w.w}
            </span>
          );
        })}
      </div>
    </div>
  );
};
