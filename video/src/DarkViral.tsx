import React from 'react';
import {Audio, staticFile} from 'remotion';
import {C, W, H} from './theme';
import {loadFonts} from './lib/fonts';
import {GlobalFrame, useG, EV, clamp, prog} from './lib/time';
import {GlitchDefs, GlitchWrap, GlitchBars} from './components/Glitch';
import {Grain, Vignette, Scanlines, Flash} from './components/Overlays';
import {Captions} from './components/Captions';
import {Scene1} from './scenes/Scene1';
import {Scene2} from './scenes/Scene2';
import {Scene3} from './scenes/Scene3';
import {Scene4} from './scenes/Scene4';
import {Scene5} from './scenes/Scene5';
import {Scene6} from './scenes/Scene6';

/** Glitch global: soma de eventos com decaimento — instantes de transição e impacto */
const GLITCH: {at: number; amp: number; decay: number; pre?: number}[] = [
  {at: EV.impact1, amp: 0.3, decay: 14},
  {at: EV.glitch12, amp: 0.85, decay: 7},
  {at: 7.0, amp: 0.45, decay: 12},
  {at: 10.97, amp: 0.8, decay: 9},
  {at: EV.cut, amp: 0.55, decay: 30, pre: 0.12},
  {at: EV.reveal, amp: 1.0, decay: 4.5},
  {at: EV.textArtificial, amp: 0.55, decay: 9},
  {at: EV.finalHit, amp: 0.5, decay: 14},
];
const glitchAt = (t: number) => {
  let g = 0;
  for (const e of GLITCH) {
    const d = t - e.at;
    if (d >= -(e.pre ?? 0) && d < 1.2) g += e.amp * (d < 0 ? 1 + d / (e.pre ?? 1) : Math.exp(-d * e.decay));
  }
  return clamp(g);
};

const Inner: React.FC = () => {
  const {t, f} = useG();
  const g = glitchAt(t);
  const wipe3 = prog(t, 6.98, 7.32); // varredura digital 2→3
  const flash = Math.max(
    clamp(1 - (t - 10.97) / 0.22) * (t >= 10.97 ? 1 : 0) * 0.75,
    clamp(1 - (t - EV.reveal) / 0.2) * (t >= EV.reveal ? 1 : 0) * 0.85,
    clamp(1 - (t - EV.finalHit) / 0.12) * (t >= EV.finalHit ? 1 : 0) * 0.35,
  );
  return (
    <div style={{position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden', width: W, height: H}}>
      <GlitchDefs />
      <GlitchWrap intensity={g} f={f}>
        {t < 3.6 && <Scene1 />}
        {t >= 3.0 && t < 7.6 && <Scene2 />}
        {t >= 6.98 && t < 11.8 && (
          <div style={{position: 'absolute', inset: 0, clipPath: wipe3 < 1 ? `inset(0 0 ${100 - wipe3 * 100}% 0)` : undefined}}>
            <Scene3 />
          </div>
        )}
        {t >= 10.9 && t < 16.2 && <Scene4 />}
        {t >= 16.0 && t < 20.5 && <Scene5 />}
        {t >= 19.9 && <Scene6 />}
        {wipe3 > 0 && wipe3 < 1 && (
          <div style={{position: 'absolute', left: 0, width: W, top: wipe3 * H - 8, height: 16, background: '#9fd2ff', boxShadow: '0 0 60px 20px rgba(8,126,255,0.9)'}} />
        )}
      </GlitchWrap>
      <GlitchBars intensity={g * 0.8} f={f} />
      <Flash amount={flash} color={t >= EV.reveal && t < EV.reveal + 0.3 ? '#dfe9ff' : '#bcd8ff'} />
      <Captions />
      <Vignette />
      <Scanlines f={f} opacity={0.1} />
      <Grain f={f} />
    </div>
  );
};

export const DarkViral: React.FC = () => {
  loadFonts();
  return (
    <GlobalFrame>
      <Audio src={staticFile('audio/master.wav')} />
      <Inner />
    </GlobalFrame>
  );
};
