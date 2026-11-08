import React, {useLayoutEffect, useRef} from 'react';
import {VERT} from './shaders';

type U = Record<string, number | [number, number]>;

type State = {
  gl: WebGL2RenderingContext;
  prog: WebGLProgram;
  locs: Record<string, WebGLUniformLocation | null>;
};

const compile = (gl: WebGL2RenderingContext, type: number, src: string) => {
  const s = gl.createShader(type)!;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    throw new Error('Shader: ' + gl.getShaderInfoLog(s));
  }
  return s;
};

/** Desenha um shader em tela cheia de forma síncrona (determinístico por frame). */
export const ShaderCanvas: React.FC<{
  frag: string;
  uniforms: U;
  width: number;
  height: number;
  scale?: number;
  style?: React.CSSProperties;
}> = ({frag, uniforms, width, height, scale = 1, style}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const st = useRef<State | null>(null);
  const w = Math.round(width * scale);
  const h = Math.round(height * scale);

  useLayoutEffect(() => {
    const canvas = ref.current!;
    if (!st.current) {
      const gl = canvas.getContext('webgl2', {
        preserveDrawingBuffer: true,
        antialias: false,
        alpha: false,
      }) as WebGL2RenderingContext;
      const prog = gl.createProgram()!;
      gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, frag));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        throw new Error('Link: ' + gl.getProgramInfoLog(prog));
      }
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(prog, 'aPos');
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      st.current = {gl, prog, locs: {}};
    }
    const {gl, prog, locs} = st.current;
    gl.viewport(0, 0, w, h);
    gl.useProgram(prog);
    const set = (name: string, v: number | [number, number]) => {
      if (!(name in locs)) locs[name] = gl.getUniformLocation(prog, name);
      const l = locs[name];
      if (!l) return;
      if (typeof v === 'number') gl.uniform1f(l, v);
      else gl.uniform2f(l, v[0], v[1]);
    };
    set('uRes', [w, h]);
    Object.entries(uniforms).forEach(([k, v]) => set(k, v));
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  });

  return (
    <canvas
      ref={ref}
      width={w}
      height={h}
      style={{width: '100%', height: '100%', display: 'block', ...style}}
    />
  );
};
