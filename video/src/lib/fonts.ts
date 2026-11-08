import {continueRender, delayRender, staticFile} from 'remotion';

const FONTS: {family: string; file: string; weight: string}[] = [
  {family: 'Anton', file: 'anton-latin-400-normal.woff2', weight: '400'},
  {family: 'Inter', file: 'inter-latin-500-normal.woff2', weight: '500'},
  {family: 'Inter', file: 'inter-latin-700-normal.woff2', weight: '700'},
  {family: 'Inter', file: 'inter-latin-800-normal.woff2', weight: '800'},
  {family: 'JetBrains Mono', file: 'jetbrains-mono-latin-400-normal.woff2', weight: '400'},
  {family: 'JetBrains Mono', file: 'jetbrains-mono-latin-700-normal.woff2', weight: '700'},
];

let started = false;
/** Carrega as fontes locais (public/fonts) antes de renderizar qualquer quadro. */
export const loadFonts = () => {
  if (started) return;
  started = true;
  const handle = delayRender('fonts');
  Promise.all(
    FONTS.map(async (f) => {
      const face = new FontFace(f.family, `url(${staticFile('fonts/' + f.file)}) format('woff2')`, {weight: f.weight});
      await face.load();
      (document.fonts as unknown as {add: (f: FontFace) => void}).add(face);
    }),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error('Falha ao carregar fontes', e);
      continueRender(handle);
    });
};
