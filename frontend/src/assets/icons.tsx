import React from 'react';
import Svg, { Path, Circle, Polygon, Polyline, Line, Rect } from 'react-native-svg';
import { C } from '../theme/tokens';

export function IconGoogle({ size = 20 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M23.04 12.27c0-.82-.07-1.42-.22-2.05H12v3.93h6.34c-.13 1.05-.83 2.63-2.38 3.7l-.02.14 3.46 2.68.24.02c2.2-2.03 3.4-5.02 3.4-8.42z" fill="#4285F4" />
      <Path d="M12 23c3.13 0 5.76-1.03 7.68-2.8l-3.66-2.84c-.98.68-2.3 1.16-4.02 1.16-3.07 0-5.67-2.03-6.6-4.84l-.14.01-3.6 2.78-.05.13C3.51 20.44 7.44 23 12 23z" fill="#34A853" />
      <Path d="M5.4 13.68A6.98 6.98 0 015 12c0-.58.1-1.15.28-1.68l-.01-.15-3.64-2.83-.12.06A11 11 0 001 12c0 1.77.42 3.45 1.16 4.94l3.24-2.26z" fill="#FBBC05" />
      <Path d="M12 5.16c2.18 0 3.65.94 4.49 1.73l3.28-3.2C17.74 1.99 15.13 1 12 1 7.44 1 3.51 3.56 1.99 7.06l3.4 2.64C6.33 6.9 8.93 5.16 12 5.16z" fill="#EA4335" />
    </Svg>
  );
}

export function IconNaver({ size = 20 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Rect width={24} height={24} rx={5} fill="#03C75A" />
      <Path d="M13.6 6.5v6.05L10.2 6.5H6.5v11h3.8v-6.05l3.4 6.05h3.7v-11h-3.8z" fill="#fff" />
    </Svg>
  );
}

export function IconEye({ on, size = 20 }: { on?: boolean; size?: number }) {
  if (!on) {
    return (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path d="M3 3l18 18" stroke={C.muted} strokeWidth={1.8} strokeLinecap="round" />
        <Path d="M10.58 10.58a2 2 0 002.83 2.83" stroke={C.muted} strokeWidth={1.8} strokeLinecap="round" />
        <Path d="M9.36 5.3A10.4 10.4 0 0112 5c5 0 9 4 10 7-.42 1.13-1.3 2.5-2.6 3.7M6.6 6.6C4.6 7.9 3.15 9.9 2 12c1 3 5 7 10 7 1.24 0 2.4-.24 3.44-.66" stroke={C.muted} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
      </Svg>
    );
  }
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z" stroke={C.muted} strokeWidth={1.8} strokeLinejoin="round" />
      <Circle cx={12} cy={12} r={3} stroke={C.muted} strokeWidth={1.8} />
    </Svg>
  );
}

const stroke = (a?: boolean) => (a ? C.blue : C.muted);

export function IconHome({ active, size = 22 }: { active?: boolean; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M3 12L12 3l9 9" stroke={stroke(active)} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M5 10v9a1 1 0 001 1h4v-5h4v5h4a1 1 0 001-1v-9" stroke={stroke(active)} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function IconChart({ active, size = 22 }: { active?: boolean; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Rect x={3} y={12} width={4} height={9} rx={1} stroke={stroke(active)} strokeWidth={1.8} />
      <Rect x={10} y={7} width={4} height={14} rx={1} stroke={stroke(active)} strokeWidth={1.8} />
      <Rect x={17} y={3} width={4} height={18} rx={1} stroke={stroke(active)} strokeWidth={1.8} />
    </Svg>
  );
}

export function IconBook({ active, size = 22 }: { active?: boolean; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M4 19.5A2.5 2.5 0 016.5 17H20" stroke={stroke(active)} strokeWidth={1.8} strokeLinecap="round" />
      <Path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke={stroke(active)} strokeWidth={1.8} />
    </Svg>
  );
}

export function IconRadar({ active, size = 22 }: { active?: boolean; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" stroke={stroke(active)} strokeWidth={1.8} strokeLinejoin="round" />
      <Polygon points="12,7 17,10 17,14 12,17 7,14 7,10" stroke={stroke(active)} strokeWidth={1.4} strokeLinejoin="round" opacity={0.5} />
      <Circle cx={12} cy={12} r={2} fill={stroke(active)} />
    </Svg>
  );
}

export function IconGear({ active, size = 22 }: { active?: boolean; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Circle cx={12} cy={12} r={3} stroke={stroke(active)} strokeWidth={1.8} />
      <Path
        d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"
        stroke={stroke(active)}
        strokeWidth={1.8}
      />
    </Svg>
  );
}

export function IconBell({ size = 18 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" stroke={C.navy} strokeWidth={1.8} strokeLinecap="round" />
      <Path d="M13.73 21a2 2 0 01-3.46 0" stroke={C.navy} strokeWidth={1.8} strokeLinecap="round" />
    </Svg>
  );
}

export function IconUpload({ size = 13 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="#fff" strokeWidth={2.2} strokeLinecap="round" />
      <Polyline points="17 8 12 3 7 8" stroke="#fff" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={12} y1={3} x2={12} y2={15} stroke="#fff" strokeWidth={2.2} strokeLinecap="round" />
    </Svg>
  );
}

export function IconBack({ size = 20 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M19 12H5M12 5l-7 7 7 7" stroke={C.navy} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function IconArrow({ size = 13 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M9 18l6-6-6-6" stroke={C.muted} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function IconCloud({ size = 38 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Polyline points="16 16 12 12 8 16" stroke={C.blue} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={12} y1={12} x2={12} y2={21} stroke={C.blue} strokeWidth={1.6} strokeLinecap="round" />
      <Path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3" stroke={C.blue} strokeWidth={1.6} strokeLinecap="round" />
    </Svg>
  );
}

export function IconExt({ size = 11 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" stroke={C.blue} strokeWidth={1.8} strokeLinecap="round" />
      <Polyline points="15 3 21 3 21 9" stroke={C.blue} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={10} y1={14} x2={21} y2={3} stroke={C.blue} strokeWidth={1.8} strokeLinecap="round" />
    </Svg>
  );
}

export function IconSearch({ size = 16 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Circle cx={11} cy={11} r={8} stroke={C.muted} strokeWidth={1.8} />
      <Path d="M21 21l-4.35-4.35" stroke={C.muted} strokeWidth={1.8} strokeLinecap="round" />
    </Svg>
  );
}

export function IconDoc({ size = 56 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M5 4a2 2 0 012-2h7l5 5v13a2 2 0 01-2 2H7a2 2 0 01-2-2V4z" stroke={C.blue} strokeWidth={1.2} />
      <Path d="M9 3.5h6v1.5a1 1 0 01-1 1h-4a1 1 0 01-1-1V3.5z" stroke={C.blue} strokeWidth={1.2} strokeLinejoin="round" />
      <Path d="M8.5 10l1.2 1.2L12 9" stroke={C.blue} strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M14 10.2h2" stroke={C.blue} strokeWidth={1.1} strokeLinecap="round" opacity={0.45} />
      <Path d="M8.5 13.5l1.2 1.2 2.3-2.2" stroke={C.blue} strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M14 13.7h2" stroke={C.blue} strokeWidth={1.1} strokeLinecap="round" opacity={0.45} />
      <Path d="M8.5 17.2h2.5" stroke="#CBD5E1" strokeWidth={1.1} strokeLinecap="round" />
      <Path d="M13.5 17.2h2" stroke="#CBD5E1" strokeWidth={1.1} strokeLinecap="round" />
    </Svg>
  );
}

export function IconClock({ size = 16 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Circle cx={12} cy={12} r={9} stroke={C.blue} strokeWidth={1.8} />
      <Path d="M12 7v5l3 3" stroke={C.blue} strokeWidth={1.8} strokeLinecap="round" />
    </Svg>
  );
}

export function IconClip({ size = 16 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
        stroke={C.blue}
        strokeWidth={1.8}
        strokeLinecap="round"
      />
    </Svg>
  );
}

export function IconCheckBig({ size = 56 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Circle cx={12} cy={12} r={10} stroke={C.blue} strokeWidth={1.2} />
      <Path d="M7.5 12.5l3 3 6-6" stroke={C.blue} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function IconPrev({ enabled, size = 14 }: { enabled?: boolean; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M19 12H5M5 12l7-7M5 12l7 7" stroke={enabled ? C.muted : C.border} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function IconFile({ size = 18 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z" stroke={C.blue} strokeWidth={1.7} strokeLinejoin="round" />
      <Path d="M14 3v5h5" stroke={C.blue} strokeWidth={1.7} strokeLinejoin="round" />
    </Svg>
  );
}

export function IconTick({ size = 24 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M5 13l4 4L19 7" stroke="#fff" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}
