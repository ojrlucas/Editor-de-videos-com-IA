import React, {useLayoutEffect, useRef} from 'react';
import {useG} from '../lib/time';
import {W, H} from '../theme';

type Props = {
  draw: (ctx: CanvasRenderingContext2D, t: number, f: number) => void;
  width?: number;
  height?: number;
  style?: React.CSSProperties;
};

/** Canvas 2D redesenhado de forma síncrona a cada quadro (determinístico para o Remotion). */
export const Canvas2D: React.FC<Props> = ({draw, width = W, height = H, style}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const {t, f} = useG();
  useLayoutEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.save();
    draw(ctx, t, f);
    ctx.restore();
  });
  return <canvas ref={ref} width={width} height={height} style={{position: 'absolute', left: 0, top: 0, width, height, ...style}} />;
};

/** Sprite de brilho pré-renderizado (muito mais barato que shadowBlur por partícula) */
const sprites = new Map<string, HTMLCanvasElement>();
export const glowSprite = (color: string, size = 64): HTMLCanvasElement => {
  const k = color + size;
  let s = sprites.get(k);
  if (!s) {
    s = document.createElement('canvas');
    s.width = s.height = size;
    const g = s.getContext('2d')!;
    const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grd.addColorStop(0, color);
    grd.addColorStop(0.18, color);
    grd.addColorStop(0.5, color.replace(/[\d.]+\)$/g, '0.25)'));
    grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, size, size);
    sprites.set(k, s);
  }
  return s;
};
