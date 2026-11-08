import React from 'react';
import {staticFile} from 'remotion';
import {C, W, H} from '../theme';
import {rng} from '../lib/time';

/** Grão de filme: textura de ruído deslocada aleatoriamente a cada quadro */
export const Grain: React.FC<{f: number; opacity?: number}> = ({f, opacity = 0.09}) => {
  const r = rng(f * 7 + 3);
  const x = Math.floor(r() * 512), y = Math.floor(r() * 512);
  return (
    <div
      style={{
        position: 'absolute', inset: 0, opacity, mixBlendMode: 'overlay',
        backgroundImage: `url(${staticFile('noise.png')})`, backgroundSize: '512px 512px',
        backgroundPosition: `${x}px ${y}px`,
      }}
    />
  );
};

export const Vignette: React.FC<{strength?: number}> = ({strength = 0.85}) => (
  <div
    style={{
      position: 'absolute', inset: 0,
      background: `radial-gradient(ellipse 75% 62% at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,${strength}) 100%)`,
    }}
  />
);

export const Scanlines: React.FC<{opacity?: number; f?: number}> = ({opacity = 0.12, f = 0}) => (
  <div
    style={{
      position: 'absolute', inset: 0, opacity, mixBlendMode: 'multiply',
      backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.9) 0px, rgba(0,0,0,0.9) 1px, rgba(0,0,0,0) 3px, rgba(0,0,0,0) 5px)',
      backgroundPosition: `0 ${(f * 2) % 5}px`,
    }}
  />
);

export const Flash: React.FC<{amount: number; color?: string}> = ({amount, color = '#fff'}) =>
  amount > 0.005 ? <div style={{position: 'absolute', inset: 0, background: color, opacity: amount}} /> : null;

/** Fundo base escuro com luz ambiente colorida */
export const AmbientBG: React.FC<{blue?: number; red?: number; cx?: number; cy?: number}> = ({blue = 0.25, red = 0, cx = 50, cy = 50}) => (
  <div style={{position: 'absolute', inset: 0, background: C.bg}}>
    <div style={{position: 'absolute', inset: 0, background: `radial-gradient(circle at ${cx}% ${cy}%, rgba(8,126,255,${blue}) 0%, rgba(8,126,255,0) 55%)`}} />
    <div style={{position: 'absolute', inset: 0, background: `radial-gradient(circle at ${cx}% ${cy + 12}%, rgba(255,38,61,${red}) 0%, rgba(255,38,61,0) 60%)`}} />
  </div>
);
export const SIZE = {W, H};
