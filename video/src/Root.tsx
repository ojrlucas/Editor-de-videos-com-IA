import React from 'react';
import {Composition} from 'remotion';
import {DarkViral} from './DarkViral';
import {W, H} from './theme';

export const Root: React.FC = () => (
  <Composition id="DarkViral" component={DarkViral} width={W} height={H} fps={30} durationInFrames={750} />
);
