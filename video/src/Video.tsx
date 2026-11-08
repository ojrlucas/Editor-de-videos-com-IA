import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
import {ShaderCanvas} from './ShaderCanvas';
import {PLANET_FRAG, CLOUD_FRAG} from './shaders';
import {W, H, FPS, clamp, lerp, range, smooth, smoother} from './timeline';
import {planetA, planetD, flyPhase, windPhase, flashAt, shakeAt, tClouds1, tPlanetD, tClouds2, TL} from './anim';
import {Particles} from './Particles';
import {Headline} from './Headline';
import {Captions} from './Captions';
import {PlanetHud} from './Hud';
import {Vignette, Grain, Flare, Flash, Disclaimer} from './Overlays';
import {Fonts} from './Fonts';

const SC = 0.6; // resolução interna do shader (a imagem é ampliada com filtragem suave)

const planetUniforms = (t: number, s: ReturnType<typeof planetA>) => ({
  uT: t, uR: s.R, uC: s.C, uRot: s.rot, uGrid: s.grid, uStarZoom: s.zoom, uFlash: 0, uDetail: s.detail,
});

const cloudUniforms = (t: number, extra: Record<string, number | [number, number]> = {}) => ({
  uT: t, uBase: -flyPhase(t) + 3.0, uWindPh: windPhase(t), uStretch: 1.5 + 2.4 * smooth(range(t, 7.5, 9)) * (t < 13.5 ? 1 : 0.2),
  uFlash: flashAt(t), uShake: shakeAt(t), uSwirl: 0, uSwirlC: [0, 0] as [number, number], uDark: 0, uGlow: 0,
  uRoll: 0, uZoom: 1, ...extra,
});

export const Video: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;

  // ---------------------------------------------------------- CENA 1 (planeta, viagem)
  const aOp = 1 - smooth(range(t, 3.95, 4.5));
  const aPunch = 1 + 0.9 * smooth(range(t, 3.7, 4.5)) ** 2;
  const sa = planetA(Math.min(t, 4.6));

  // ---------------------------------------------------------- CENAS 2 e 3 (nuvens)
  const b1In = smooth(range(t, tClouds1.in, tClouds1.in + 0.6));
  const b1Out = 1 - smooth(range(t, 12.9, 13.5));
  const b1Op = b1In * b1Out;
  const b1Scale = lerp(1.35, 1, smooth(range(t, tClouds1.in, tClouds1.in + 0.9))) * lerp(1, 1.12, smooth(range(t, 12.9, 13.5)));
  const tilt = t > 8 && t < 13.4 ? 0.07 * Math.sin(t * 0.45) + 0.05 * smooth(range(t, 11.7, 12.6)) : 0.015 * Math.sin(t * 0.3);
  const zoom1 = 1 + 0.05 * range(t, 4.4, 8) + 0.07 * range(t, 8, 13.3);
  const cloud1 = cloudUniforms(t, {uRoll: tilt, uZoom: zoom1, uGlow: smooth(range(t, 7.8, 9.5)) * 0.8});

  // ---------------------------------------------------------- CENA 4 (planeta inteiro)
  const dIn = smooth(range(t, tPlanetD.in, tPlanetD.in + 0.55));
  const dOut = 1 - smooth(range(t, 17.95, 18.6));
  const sd = planetD(clamp(t, 12.8, 18.7));
  const dScale = lerp(0.9, 1, smooth(range(t, tPlanetD.in, tPlanetD.in + 0.6)));

  // ---------------------------------------------------------- CENA 5 (tempestade final)
  const eIn = smooth(range(t, tClouds2.in, tClouds2.in + 0.7));
  const eScale = lerp(1.45, 1, smooth(range(t, tClouds2.in, tClouds2.in + 1.0)));
  const sw = smooth(range(t, 18.2, 22));
  const cloud2 = cloudUniforms(t, {
    uSwirl: 0.4 + 2.6 * sw, uSwirlC: [lerp(0.35, 0.0, sw), lerp(0.6, 0.2, sw)], uGlow: 0.6 + 0.8 * sw,
    uRoll: -0.06 * Math.sin(t * 0.35) - 0.04 * sw, uZoom: 1 + 0.55 * smooth(range(t, 18.5, 25)),
    uDark: 0.1 * smooth(range(t, 22, 25)), uStretch: 2.2,
  });

  // ---------------------------------------------------------- flashes de transição
  const tf = (c: number, w = 0.22) => Math.max(0, 1 - Math.abs(t - c) / w);
  const flash = 0.8 * tf(4.15, 0.28) + 0.65 * tf(13.0, 0.25) + 0.7 * tf(18.3, 0.28) + 0.9 * tf(0.5, 0.12) + 0.5 * tf(8.15, 0.18) + 0.5 * tf(22.35, 0.12);
  const lightning = flashAt(t);

  // ---------------------------------------------------------- títulos (storyboard)
  const q = TL.sentences[5];
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <Fonts />
      <Audio src={staticFile('audio/audio_final.wav')} />

      {/* fundo 3D procedural */}
      {t < 4.6 && (
        <AbsoluteFill style={{opacity: aOp, transform: `scale(${aPunch})`, filter: `blur(${(aPunch - 1) * 10}px)`}}>
          <ShaderCanvas frag={PLANET_FRAG} width={W} height={H} scale={SC} uniforms={planetUniforms(t, sa)} />
        </AbsoluteFill>
      )}
      {t >= tClouds1.in - 0.05 && t <= 13.6 && (
        <AbsoluteFill style={{opacity: b1Op, transform: `scale(${b1Scale})`, filter: `blur(${(1 - b1In) * 8 + (1 - b1Out) * 12}px)`}}>
          <ShaderCanvas frag={CLOUD_FRAG} width={W} height={H} scale={SC} uniforms={cloud1} />
        </AbsoluteFill>
      )}
      {t >= tPlanetD.in - 0.05 && t <= 18.7 && (
        <AbsoluteFill style={{opacity: dIn * dOut, transform: `scale(${dScale})`, filter: `blur(${(1 - dIn) * 10}px)`}}>
          <ShaderCanvas frag={PLANET_FRAG} width={W} height={H} scale={SC} uniforms={planetUniforms(t, sd)} />
        </AbsoluteFill>
      )}
      {t >= tClouds2.in - 0.05 && (
        <AbsoluteFill style={{opacity: eIn, transform: `scale(${eScale})`, filter: `blur(${(1 - eIn) * 12}px)`}}>
          <ShaderCanvas frag={CLOUD_FRAG} width={W} height={H} scale={SC} uniforms={cloud2} />
        </AbsoluteFill>
      )}

      {/* partículas de silicato + fragmentos de cristal */}
      <Particles t={t} />
      <Flare flash={lightning} t={t} />

      {/* HUD científico (cena 4) */}
      <PlanetHud t={t} R={sd.R} C={sd.C} />

      {/* títulos */}
      <Headline t={t} start={0.5} end={4.0} y={470} size={100} fadeOut={0.35}
        lines={[[{text: 'EXISTE'}, {text: 'UM'}], [{text: 'PLANETA'}, {text: 'ONDE'}], [{text: 'CHOVE'}, {text: 'VIDRO!', hl: true}]]} />
      <Headline t={t} start={4.3} end={7.9} y={470} size={96} style="slow" stagger={0.14}
        lines={[[{text: 'E'}, {text: 'NÃO'}, {text: 'É'}, {text: 'UMA'}], [{text: 'CHUVA', hl: true}, {text: 'NORMAL...', hl: true}]]} />
      <Headline t={t} start={8.2} end={12.9} y={470} size={104} style="wind" stagger={0.2}
        lines={[[{text: 'VENTOS'}], [{text: 'EXTREMAMENTE', hl: true}], [{text: 'VIOLENTOS!'}]]} />
      <Headline t={t} start={19.0} end={22.0} y={440} size={86} stagger={0.1} fadeOut={0.35}
        lines={[[{text: 'UM'}, {text: 'DOS'}, {text: 'MUNDOS'}], [{text: 'MAIS'}, {text: 'EXTREMOS', hl: true}], [{text: 'JÁ'}, {text: 'ESTUDADOS.'}]]} />
      <Headline t={t} start={q.start - 0.05} end={null} y={540} size={118} stagger={0.2}
        lines={[[{text: 'VOCÊ'}, {text: 'TERIA'}], [{text: 'CORAGEM', hl: true}, {text: 'DE'}], [{text: 'VISITÁ-LO?', hl: true}]]} />

      <Captions t={t} />
      <Disclaimer a={clamp(range(t, 0.8, 1.4)) * 0.9} />
      <Flash a={flash} />
      <Vignette amount={0.85} />
      <Grain frame={frame} />
    </AbsoluteFill>
  );
};
