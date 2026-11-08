import React from 'react';
import {staticFile} from 'remotion';

export const Fonts: React.FC = () => (
  <style>{`
    @font-face{font-family:'Montserrat';font-weight:800;src:url(${staticFile('fonts/montserrat-latin-800-normal.woff2')}) format('woff2');}
    @font-face{font-family:'Montserrat';font-weight:900;src:url(${staticFile('fonts/montserrat-latin-900-normal.woff2')}) format('woff2');}
    @font-face{font-family:'Rajdhani';font-weight:500;src:url(${staticFile('fonts/rajdhani-latin-500-normal.woff2')}) format('woff2');}
    @font-face{font-family:'Rajdhani';font-weight:600;src:url(${staticFile('fonts/rajdhani-latin-600-normal.woff2')}) format('woff2');}
    @font-face{font-family:'Rajdhani';font-weight:700;src:url(${staticFile('fonts/rajdhani-latin-700-normal.woff2')}) format('woff2');}
  `}</style>
);
export const HEAD = "'Montserrat', 'Arial Black', sans-serif";
export const HUDF = "'Rajdhani', 'Montserrat', sans-serif";
