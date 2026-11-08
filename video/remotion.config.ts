import {Config} from '@remotion/cli/config';
import fs from 'node:fs';

// Usa o Chromium local quando existir (ambientes sem acesso ao download do Chrome do Remotion).
const candidates = [
  process.env.REMOTION_BROWSER,
  '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',
].filter(Boolean) as string[];
const found = candidates.find((p) => fs.existsSync(p));
if (found) Config.setBrowserExecutable(found);

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer('angle');
