import React from 'react';
import {C, F} from '../theme';
import {clamp, easeOut, map} from '../lib/time';

export const PHONE_W = 390;
export const PHONE_H = 800;

const Btn: React.FC<{color: string; icon: React.ReactNode; label: string; pulse?: number}> = ({color, icon, label, pulse = 0}) => (
  <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10}}>
    <div style={{width: 84, height: 84, borderRadius: 42, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 ${24 + pulse * 30}px ${color}`}}>
      {icon}
    </div>
    <div style={{fontFamily: F.body, fontSize: 16, color: 'rgba(255,255,255,0.8)', fontWeight: 500}}>{label}</div>
  </div>
);
const Handset: React.FC<{rot: number}> = ({rot}) => (
  <svg width="40" height="40" viewBox="0 0 24 24" style={{transform: `rotate(${rot}deg)`}}>
    <path fill="#fff" d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z" />
  </svg>
);

/**
 * Interface de chamada (original, sem marcas). lt = segundos desde que a tela acendeu.
 * mode 'incoming' = chamada recebida; 'connected' = em andamento (com ondas da voz).
 */
export const PhoneUI: React.FC<{lt: number; mode: 'incoming' | 'connected'; level?: number; name?: string; seconds?: number; accent?: string}> = ({
  lt, mode, level = 0, name = 'Mãe', seconds = 0, accent = C.blue,
}) => {
  const ring = (lt * 0.9) % 1;
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(Math.floor(seconds % 60)).padStart(2, '0');
  return (
    <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(170deg,#0a1530 0%,#0b1020 45%,#150a14 100%)', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: -80, top: -60, width: 400, height: 400, borderRadius: 200, background: `radial-gradient(circle, ${accent}55, transparent 70%)`}} />
      <div style={{position: 'absolute', top: 106, width: '100%', textAlign: 'center', fontFamily: F.body, color: 'rgba(255,255,255,0.7)', fontSize: 18, fontWeight: 500, letterSpacing: 0.5}}>
        {mode === 'incoming' ? 'Chamada recebida' : 'Chamada em andamento'}
      </div>
      <div style={{position: 'absolute', top: 138, width: '100%', textAlign: 'center', fontFamily: F.body, color: '#fff', fontSize: 58, fontWeight: 700, letterSpacing: -1}}>{name}</div>
      <div style={{position: 'absolute', top: 214, width: '100%', textAlign: 'center', fontFamily: F.body, color: 'rgba(255,255,255,0.6)', fontSize: 20, fontWeight: 500}}>
        {mode === 'incoming' ? 'celular' : `${mm}:${ss}`}
      </div>
      {/* avatar com anéis pulsantes */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 290, height: 200, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
        {[0, 0.5].map((o, i) => {
          const k = (ring + o) % 1;
          return <div key={i} style={{position: 'absolute', width: 120 + k * 150, height: 120 + k * 150, borderRadius: 999, border: `2px solid ${accent}`, opacity: (1 - k) * 0.7}} />;
        })}
        <div style={{width: 128, height: 128, borderRadius: 64, background: 'linear-gradient(145deg,#2a3a63,#101830)', border: '2px solid rgba(255,255,255,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
          <svg width="128" height="128" viewBox="0 0 128 128">
            <circle cx="64" cy="50" r="22" fill="rgba(255,255,255,0.78)" />
            <path d="M18 128c2-34 22-48 46-48s44 14 46 48z" fill="rgba(255,255,255,0.78)" />
          </svg>
        </div>
      </div>
      {mode === 'connected' && (
        <div style={{position: 'absolute', left: 30, right: 30, top: 520, height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5}}>
          {Array.from({length: 27}, (_, i) => {
            const c = (i - 13) / 13;
            const h = 6 + (60 * level + 8) * (1 - Math.abs(c) * 0.75) * (0.55 + 0.45 * Math.sin(lt * 14 + i * 1.9));
            return <div key={i} style={{width: 6, height: Math.max(5, h), borderRadius: 3, background: accent, boxShadow: `0 0 10px ${accent}`}} />;
          })}
        </div>
      )}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 70, display: 'flex', justifyContent: 'center', gap: mode === 'incoming' ? 120 : 0}}>
        {mode === 'incoming' ? (
          <>
            <Btn color="#E5334B" icon={<Handset rot={135} />} label="Recusar" />
            <Btn color="#2DBE60" icon={<Handset rot={0} />} label="Atender" pulse={Math.abs(Math.sin(lt * 7))} />
          </>
        ) : (
          <Btn color="#E5334B" icon={<Handset rot={135} />} label="Encerrar" />
        )}
      </div>
    </div>
  );
};

/** Corpo do celular (vidro preto, borda metálica, ilha). children = tela */
export const PhoneBody: React.FC<{screenOn: number; children: React.ReactNode; glare?: number}> = ({screenOn, children, glare = 0.5}) => (
  <div style={{position: 'relative', width: PHONE_W, height: PHONE_H, borderRadius: 60, background: 'linear-gradient(145deg,#2b303b,#0b0d12 40%,#1b1f29)', boxShadow: '0 0 0 2px #3a4150, inset 0 0 0 3px #05060a, 0 40px 80px rgba(0,0,0,0.7)'}}>
    <div style={{position: 'absolute', inset: 13, borderRadius: 48, background: '#02030a', overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, opacity: screenOn}}>{children}</div>
      <div style={{position: 'absolute', left: '50%', top: 14, width: 108, height: 30, marginLeft: -54, borderRadius: 16, background: '#000'}} />
      <div style={{position: 'absolute', inset: 0, background: `linear-gradient(115deg, rgba(255,255,255,${0.10 * glare}) 0%, rgba(255,255,255,0) 32%, rgba(255,255,255,0) 70%, rgba(255,255,255,${0.05 * glare}) 100%)`}} />
    </div>
  </div>
);
export const wakeOn = (t: number, t0: number) => clamp(map(t, t0, t0 + 0.12, 0, 1));
export const _unused = easeOut;
