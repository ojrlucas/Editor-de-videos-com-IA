import React from 'react';
import {C, F, W, H} from '../theme';
import {Canvas2D, glowSprite} from '../components/Canvas2D';
import {PhoneBody, PhoneUI, PHONE_H, PHONE_W} from '../components/PhoneUI';
import {EV, clamp, easeInOut, envAt, lerp, map, noise1, prog, rng, useG, win} from '../lib/time';

const T0 = 11.0;
// batimentos: mesmos instantes sintetizados no áudio
const beats: number[] = (() => {
  const out: number[] = [];
  let t = EV.heartStart;
  while (t < EV.cut) {
    out.push(t);
    const k = (t - EV.heartStart) / (EV.cut - EV.heartStart);
    t += 60 / (62 + 60 * Math.pow(k, 1.2));
  }
  return out;
})();
const beatAt = (t: number) => beats.reduce((a, b) => (t >= b ? Math.max(a, Math.exp(-(t - b) * 7)) : a), 0);

const dust = (() => {
  const r = rng(77);
  return Array.from({length: 70}, () => ({x: r() * W, y: r() * H, z: 0.3 + r() * 0.7, ph: r() * 6}));
})();

/** CENA 4 — A ligação (11–16s): ambiente doméstico escuro, pessoa iluminada pelo celular, dolly-in, tensão crescente. */
export const Scene4: React.FC = () => {
  const {t, f} = useG();
  const lt = t - T0;
  const k = prog(t, T0, 16.0);
  const dolly = easeInOut(k);
  const scale = lerp(1.0, 1.46, dolly);
  const sway = noise1(t * 0.9) * 7;
  const worry = clamp(map(t, 11.9, 15.6, 0, 1)); // 0 neutro → 1 apavorado
  const beat = beatAt(t);
  const callLvl = envAt('call', f);
  const connected = t >= EV.callConnect;
  const redLvl = clamp(map(t, 12, 15.9, 0.05, 0.6));
  const flick = 0.88 + 0.12 * Math.sin(t * 31) * (connected ? callLvl : 0.4) + 0.1 * beat;
  const op = win(t, T0, 16.1, 0.001, 0.001);
  // sobrancelhas: ângulo interno sobe com a preocupação
  const brow = (side: number) => `rotate(${side * (worry * 17 - 2)}deg)`;
  const cx = 540, cy = 770; // centro do rosto

  return (
    <div style={{position: 'absolute', inset: 0, opacity: op}}>
      {/* sala escura (fora de foco) */}
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg,#05070d 0%,#090c15 55%,#04050a 100%)'}} />
      <div style={{position: 'absolute', inset: 0, transform: `scale(${1 + (scale - 1) * 0.35}) translateX(${sway * 0.4}px)`, filter: 'blur(11px)', transformOrigin: '50% 45%'}}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
          <defs>
            <linearGradient id="moon" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#2a74d8" stopOpacity="0.9" /><stop offset="1" stopColor="#0a2a66" stopOpacity="0.1" /></linearGradient>
            <linearGradient id="shaft" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#4a98ff" stopOpacity="0.28" /><stop offset="1" stopColor="#4a98ff" stopOpacity="0" /></linearGradient>
          </defs>
          {/* janela com persiana */}
          <rect x="30" y="250" width="400" height="560" fill="#0a1a38" />
          {Array.from({length: 11}, (_, i) => <rect key={i} x="36" y={258 + i * 50} width="388" height="36" fill="url(#moon)" opacity={0.55 + 0.35 * Math.sin(i)} />)}
          <polygon points="430,300 900,900 760,1300 430,800" fill="url(#shaft)" />
          {/* sofá e abajur */}
          <rect x="-40" y="1150" width="560" height="260" rx="60" fill="#080b14" />
          <rect x="-60" y="1060" width="200" height="340" rx="70" fill="#0b0f1a" />
          <rect x="880" y="700" width="14" height="560" fill="#0b0f1a" />
          <ellipse cx="887" cy="690" rx="70" ry="40" fill="#101424" />
          <circle cx="930" cy="1210" r="6" fill={C.red} opacity={0.5 + 0.5 * Math.sin(t * 5)} />
          <rect x="700" y="1000" width="420" height="500" rx="30" fill="#070a12" />
        </svg>
      </div>
      {/* poeira em suspensão iluminada */}
      <Canvas2D
        draw={(ctx) => {
          ctx.globalCompositeOperation = 'lighter';
          dust.forEach((d) => {
            const px = (d.x + Math.sin(t * 0.4 + d.ph) * 30 * d.z) % W;
            const py = (d.y - t * 10 * d.z + H * 3) % H;
            const s = 14 * d.z + 4;
            ctx.drawImage(glowSprite(`rgba(120,190,255,${0.25 * d.z})`, 32), px - s / 2, py - s / 2, s, s);
          });
        }}
      />
      {/* PESSOA + celular (câmera dolly-in) */}
      <div style={{position: 'absolute', inset: 0, transform: `translate(${sway}px, ${-dolly * 90}px) scale(${scale})`, transformOrigin: '50% 62%'}}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position: 'absolute', inset: 0}}>
          <defs>
            <linearGradient id="skin" x1="0.5" y1="0" x2="0.5" y2="1">
              <stop offset="0" stopColor="#1a1214" /><stop offset="0.45" stopColor="#3a2a2c" /><stop offset="1" stopColor="#6f87b4" />
            </linearGradient>
            <linearGradient id="hood" x1="0.5" y1="0" x2="0.5" y2="1"><stop offset="0" stopColor="#1a2336" /><stop offset="1" stopColor="#06080e" /></linearGradient>
            <linearGradient id="rimB" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#3d9bff" stopOpacity="0.95" /><stop offset="0.25" stopColor="#3d9bff" stopOpacity="0" /></linearGradient>
            <linearGradient id="rimR" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stopColor="#ff263d" stopOpacity="0.9" /><stop offset="0.22" stopColor="#ff263d" stopOpacity="0" /></linearGradient>
            <radialGradient id="uplight" cx="0.5" cy="1" r="0.9"><stop offset="0" stopColor="#8fc4ff" stopOpacity="0.85" /><stop offset="0.6" stopColor="#3d8fff" stopOpacity="0.15" /><stop offset="1" stopColor="#3d8fff" stopOpacity="0" /></radialGradient>
            <clipPath id="faceClip"><ellipse cx={cx} cy={cy} rx="120" ry="150" /></clipPath>
          </defs>
          {/* cabelo atrás */}
          <ellipse cx={cx} cy={cy - 30} rx="158" ry="182" fill="#07080d" />
          {/* pescoço */}
          <path d={`M${cx - 62} ${cy + 110} L${cx - 70} ${cy + 240} L${cx + 70} ${cy + 240} L${cx + 62} ${cy + 110} Z`} fill="#241a1c" />
          <path d={`M${cx - 62} ${cy + 150} L${cx - 70} ${cy + 240} L${cx + 70} ${cy + 240} L${cx + 62} ${cy + 150} Z`} fill="url(#uplight)" opacity={0.5 * flick} />
          {/* moletom / ombros */}
          <path d={`M-60 1920 C-30 1400 160 1040 ${cx - 112} ${cy + 212} Q${cx} ${cy + 262} ${cx + 112} ${cy + 212} C920 1040 1110 1400 1140 1920 Z`} fill="url(#hood)" />
          <path d={`M-60 1920 C-30 1400 160 1040 ${cx - 112} ${cy + 212}`} fill="none" stroke="url(#rimB)" strokeWidth="8" opacity="0.85" />
          <path d={`M${cx + 112} ${cy + 212} C920 1040 1110 1400 1140 1920`} fill="none" stroke={C.red} strokeWidth="6" opacity={0.25 + redLvl * 0.6} />
          <path d={`M${cx - 78} ${cy + 190} Q${cx} ${cy + 290} ${cx + 78} ${cy + 190} Q${cx} ${cy + 250} ${cx - 78} ${cy + 190} Z`} fill="#070a12" />
          <path d={`M${cx - 70} ${cy + 250} Q${cx - 40} ${cy + 340} ${cx - 90} ${cy + 520}`} fill="none" stroke="#0a0d16" strokeWidth="14" opacity="0.8" />
          <path d={`M${cx + 70} ${cy + 250} Q${cx + 40} ${cy + 340} ${cx + 90} ${cy + 520}`} fill="none" stroke="#0a0d16" strokeWidth="14" opacity="0.8" />
          {/* rosto */}
          <ellipse cx={cx} cy={cy} rx="120" ry="150" fill="url(#skin)" />
          <g clipPath="url(#faceClip)">
            <ellipse cx={cx} cy={cy + 160} rx="190" ry="190" fill="url(#uplight)" opacity={0.9 * flick} />
            <rect x={cx - 130} y={cy - 160} width="70" height="320" fill="url(#rimB)" opacity="0.75" />
            <rect x={cx + 70} y={cy - 160} width="70" height="320" fill="url(#rimR)" opacity={0.3 + redLvl * 0.6} />
            {/* nariz (iluminado por baixo) */}
            <path d={`M${cx - 4} ${cy - 30} L${cx - 22} ${cy + 36} Q${cx} ${cy + 52} ${cx + 22} ${cy + 36} L${cx + 6} ${cy - 30}`} fill="rgba(160,200,255,0.2)" />
            <ellipse cx={cx} cy={cy + 44} rx="26" ry="9" fill="rgba(200,225,255,0.38)" />
            {/* olhos (olhando para baixo, para o celular) */}
            {[-1, 1].map((s) => (
              <g key={s}>
                <ellipse cx={cx + s * 46} cy={cy - 12 + worry * 2} rx="22" ry={10 + worry * 4} fill="#cfdcf2" opacity="0.88" />
                <ellipse cx={cx + s * 44} cy={cy - 8 + worry * 2} rx={9} ry={9 + worry * 1.5} fill="#10131c" />
                <circle cx={cx + s * 41} cy={cy - 11} r="2.6" fill="#fff" opacity="0.9" />
                <path d={`M${cx + s * 22} ${cy - 18 + worry * 2} Q${cx + s * 46} ${cy - 34 - worry * 4} ${cx + s * 70} ${cy - 16 + worry * 2}`} fill="none" stroke="#0b0809" strokeWidth="7" strokeLinecap="round" />
              </g>
            ))}
            {/* sobrancelhas (preocupação: lado interno sobe) */}
            <g transform={`translate(${cx - 48},${cy - 52 - worry * 4})`}><rect x="-30" y="-5" width="60" height="10" rx="5" fill="#0b0809" style={{transform: brow(-1), transformBox: 'fill-box', transformOrigin: 'center'}} /></g>
            <g transform={`translate(${cx + 48},${cy - 52 - worry * 4})`}><rect x="-30" y="-5" width="60" height="10" rx="5" fill="#0b0809" style={{transform: brow(1), transformBox: 'fill-box', transformOrigin: 'center'}} /></g>
            {/* boca */}
            <path d={`M${cx - 38} ${cy + 98 + worry * 8} Q${cx} ${cy + 90 - worry * 12 + worry * 26} ${cx + 38} ${cy + 98 + worry * 8}`} fill={worry > 0.6 ? 'rgba(10,6,8,0.85)' : 'none'} stroke="#150d10" strokeWidth="7" strokeLinecap="round" />
          </g>
          {/* franja */}
          <path d={`M${cx - 126} ${cy - 40} C${cx - 140} ${cy - 190} ${cx + 100} ${cy - 215} ${cx + 128} ${cy - 40} C${cx + 100} ${cy - 120} ${cx + 20} ${cy - 150} ${cx - 40} ${cy - 130} C${cx - 90} ${cy - 120} ${cx - 118} ${cy - 90} ${cx - 126} ${cy - 40} Z`} fill="#06070b" />
          <path d={`M${cx - 126} ${cy - 40} C${cx - 140} ${cy - 190} ${cx + 100} ${cy - 215} ${cx + 128} ${cy - 40}`} fill="none" stroke="#3d7fd6" strokeWidth="3" opacity="0.5" />
        </svg>
        {/* brilho do celular iluminando o rosto/peito */}
        <div style={{position: 'absolute', left: 0, top: 900, width: W, height: 700, background: `radial-gradient(ellipse 55% 55% at 50% 40%, rgba(95,170,255,${0.35 * flick}), rgba(8,126,255,0))`, mixBlendMode: 'screen'}} />
        {/* celular na mão */}
        <div style={{position: 'absolute', left: W / 2 - PHONE_W / 2 + 20, top: 1020, transform: `perspective(1200px) rotateX(18deg) rotateY(-12deg) rotateZ(5deg) scale(0.9)`, transformOrigin: '50% 0%'}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: PHONE_W, height: PHONE_H, borderRadius: 60, boxShadow: `0 0 120px 20px rgba(60,150,255,${0.45 * flick})`}} />
          <PhoneBody screenOn={1} glare={0.5}>
            <PhoneUI lt={lt} mode={connected ? 'connected' : 'incoming'} level={callLvl} seconds={Math.max(0, t - EV.callConnect)} accent={C.blue} />
          </PhoneBody>
          {/* dedos */}
          <svg width={PHONE_W} height={PHONE_H} style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}} viewBox={`0 0 ${PHONE_W} ${PHONE_H}`}>
            <ellipse cx="-4" cy="420" rx="28" ry="62" fill="#1b1416" stroke="#3d7fd6" strokeWidth="2" opacity="0.95" />
            <ellipse cx={PHONE_W + 6} cy="360" rx="22" ry="34" fill="#1b1416" />
            <ellipse cx={PHONE_W + 4} cy="440" rx="22" ry="34" fill="#1b1416" />
            <ellipse cx={PHONE_W + 4} cy="520" rx="22" ry="34" fill="#1b1416" />
          </svg>
        </div>
      </div>
      {/* tensão: vinheta vermelha pulsando com os batimentos */}
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 75% 60% at 50% 50%, rgba(255,38,61,0) 35%, rgba(255,38,61,${(0.1 + redLvl * 0.35) * (0.5 + beat * 0.9)}) 100%)`, mixBlendMode: 'screen'}} />
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 100% 80% at 50% 50%, rgba(0,0,0,0) 30%, rgba(0,0,0,${0.5 + beat * 0.3}) 100%)`}} />
      {/* HUD discreto */}
      <div style={{position: 'absolute', left: 70, top: 300, fontFamily: F.mono, fontWeight: 700, fontSize: 28, letterSpacing: 3, color: 'rgba(160,205,255,0.85)', textShadow: '0 2px 16px #000', opacity: win(t, 11.3, 15.8, 0.4, 0.3)}}>
        <span style={{color: C.red, opacity: 0.5 + 0.5 * Math.sin(t * 8)}}>● </span>LIGAÇÃO · 03:12
      </div>
      <div style={{position: 'absolute', right: 70, top: 300, fontFamily: F.mono, fontWeight: 700, fontSize: 28, letterSpacing: 3, color: 'rgba(255,90,110,0.9)', textShadow: '0 2px 16px #000', opacity: win(t, 12.5, 15.8, 0.4, 0.3)}}>
        {Math.round(72 + 70 * Math.pow(k, 1.3) + 6 * beat)} BPM
      </div>
    </div>
  );
};
export const _s4 = [W, H];
