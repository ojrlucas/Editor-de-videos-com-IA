import React from 'react';
import {Composition} from 'remotion';
import {Video} from './Video';
import {FPS, TOTAL_FRAMES, W, H} from './timeline';

export const Root: React.FC = () => (
  <Composition
    id="PlanetaChuvaVidro"
    component={Video}
    durationInFrames={TOTAL_FRAMES}
    fps={FPS}
    width={W}
    height={H}
  />
);
