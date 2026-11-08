import React from 'react';
import {W, H, clamp, easeOutCubic, lerp, range, smooth} from './timeline';
import {HUDF, HEAD} from './Fonts';

type P = {t: number; R: number; C: [number, number]};

const Chip: React.FC<{t: number; at: number; y: number; tag: string; tagColor: string; text: string; sub?: string}> = ({t, at, y, tag, tagColor, text, sub}) => {
  const p = easeOutCubic(range(t, at, at + 0.5));
  if (p <= 0) return null;
  return (
    <div style={{position: 'absolute', left: 90, width: W - 180, top: y, opacity: p, transform: `translateX(${(1 - p) * -60}px)`,
      display: 'flex', alignItems: 'center', gap: 22, padding: '14px 26px', borderRadius: 14,
      background: 'linear-gradient(90deg, rgba(8,28,70,.72), rgba(8,28,70,.35))', border: '1.5px solid rgba(110,190,255,.45)',
      boxShadow: '0 0 30px rgba(40,120,255,.25)', backdropFilter: 'blur(6px)', fontFamily: HUDF}}>
      <div style={{fontSize: 24, fontWeight: 700, letterSpacing: 3, color: '#04122e', background: tagColor, padding: '6px 14px', borderRadius: 6, whiteSpace: 'nowrap'}}>{tag}</div>
      <div>
        <div style={{fontSize: 38, fontWeight: 700, color: '#fff', lineHeight: 1.05, textTransform: 'uppercase', letterSpacing: 1}}>{text}</div>
        {sub && <div style={{fontSize: 24, fontWeight: 500, color: 'rgba(170,215,255,.85)', letterSpacing: 1}}>{sub}</div>}
      </div>
    </div>
  );
};

/** Identificação científica da cena 4 (visualização de dados sobre o planeta). */
export const PlanetHud: React.FC<P> = ({t, R, C}) => {
  const a = smooth(range(t, 15.0, 15.7)) * (1 - smooth(range(t, 17.55, 18.05)));
  if (a <= 0.001) return null;
  const cx = W / 2 + C[0] * (W / 2), cy = H / 2 - C[1] * (W / 2), r = R * (W / 2);
  const ring = r * 1.14;
  const dash = 2 * Math.PI * ring;
  const name = easeOutCubic(range(t, 14.3, 15.2));
  const lineP = easeOutCubic(range(t, 15.2, 15.9));
  // ponto do limbo (superior esquerdo) e rótulo
  const ang = -Math.PI * 0.78;
  const px = cx + Math.cos(ang) * r, py = cy + Math.sin(ang) * r;
  return (
    <>
      <div style={{position: 'absolute', inset: 0, opacity: a}}>
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <g transform={`rotate(${t * 6} ${cx} ${cy})`} opacity={0.85}>
            <circle cx={cx} cy={cy} r={ring} fill="none" stroke="rgba(120,200,255,.7)" strokeWidth={2}
              strokeDasharray={`${dash * 0.012} ${dash * 0.018}`} />
          </g>
          <circle cx={cx} cy={cy} r={ring * 1.05} fill="none" stroke="rgba(120,200,255,.25)" strokeWidth={1.5} />
          {Array.from({length: 36}).map((_, i) => {
            const aa = (i / 36) * Math.PI * 2 + t * 0.05;
            const l = i % 3 === 0 ? 26 : 12;
            return <line key={i} x1={cx + Math.cos(aa) * ring * 1.05} y1={cy + Math.sin(aa) * ring * 1.05}
              x2={cx + Math.cos(aa) * (ring * 1.05 + l)} y2={cy + Math.sin(aa) * (ring * 1.05 + l)} stroke="rgba(130,205,255,.6)" strokeWidth={2} />;
          })}
          <polyline fill="none" stroke="rgba(150,220,255,.9)" strokeWidth={2.5}
            points={`${px},${py} ${lerp(px, 300, lineP)},${lerp(py, 330, lineP)} ${lerp(300, 150, lineP)},${lerp(330, 330, lineP)}`} />
          <circle cx={px} cy={py} r={9} fill="none" stroke="#9be0ff" strokeWidth={3} />
          <circle cx={px} cy={py} r={4} fill="#fff" />
          {/* cantos de enquadramento */}
          {[[60, 120, 1, 1], [W - 60, 120, -1, 1], [60, 1380, 1, -1], [W - 60, 1380, -1, -1]].map(([x, y, sx, sy], i) => (
            <path key={i} d={`M${x} ${y + sy * 60} L${x} ${y} L${x + sx * 60} ${y}`} fill="none" stroke="rgba(140,210,255,.7)" strokeWidth={3} />
          ))}
        </svg>
      </div>
      {/* nome do planeta */}
      <div style={{position: 'absolute', left: 0, width: W, top: 150, textAlign: 'center', opacity: name * a, transform: `translateY(${(1 - name) * -24}px)`}}>
        <div style={{fontFamily: HUDF, fontWeight: 600, fontSize: 30, letterSpacing: 8, color: '#8fd2ff'}}>EXOPLANETA</div>
        <div style={{fontFamily: HEAD, fontWeight: 900, fontSize: 112, letterSpacing: 2, color: '#fff', lineHeight: 1.05,
          textShadow: '0 0 30px rgba(70,170,255,.95), 0 0 70px rgba(40,120,255,.6), 0 6px 14px rgba(0,10,40,.8)'}}>HD 189733 b</div>
      </div>
      <div style={{position: 'absolute', left: 90, top: 345, opacity: lineP * a, fontFamily: HUDF, fontWeight: 700, fontSize: 30, letterSpacing: 4,
        color: '#b8e6ff', textShadow: '0 0 14px rgba(70,170,255,.9)'}}>ATMOSFERA AZULADA</div>
      <div style={{opacity: a}}>
        <Chip t={t} at={15.5} y={1188} tag="OBSERVADO" tagColor="#7fd2ff" text="Cor azulada medida pelo Hubble" />
        <Chip t={t} at={16.25} y={1292} tag="HIPÓTESE" tagColor="#ffd37a" text="Nuvens de silicato · modelos atmosféricos" />
      </div>
    </>
  );
};
