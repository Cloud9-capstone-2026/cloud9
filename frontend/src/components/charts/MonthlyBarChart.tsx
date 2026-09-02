import React from 'react';
import Svg, { Rect, Polyline, Circle, Text as SvgText, Defs, LinearGradient, Stop } from 'react-native-svg';
import { C, ACCENT } from '../../theme/tokens';
import type { MonthlyDatum } from '../../data/types';

// 이 차트의 고정 렌더 높이 — 카드가 빈 상태일 때 크기를 유지해야 하면 이 값을 그대로 재사용할 것.
export const MONTHLY_CHART_HEIGHT = 158;

export function MonthlyBarChart({ data, activeTab }: { data: MonthlyDatum[]; activeTab: 'trades' | 'anomaly' }) {
  const W = 356, H = MONTHLY_CHART_HEIGHT, padL = 26, padB = 24, padT = 8;
  const plotH = H - padB - padT;
  const n = data.length;
  const step = (W - padL - 8) / n;
  const maxV = 20;
  const y = (v: number) => padT + plotH - (v / maxV) * plotH;

  const barOpacity = activeTab === 'trades' ? 1 : 0.13;
  const lineOpacity = activeTab === 'anomaly' ? 1 : 0.1;

  const points = data.map((d, i) => `${padL + i * step + step / 2},${y(d.anomalies)}`).join(' ');

  return (
    <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height={158}>
      <Defs>
        <LinearGradient id="canaryBarGrad" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0%" stopColor="#1d4ed8" />
          <Stop offset="72%" stopColor="#1d4ed8" />
          <Stop offset="100%" stopColor="#3b82f6" stopOpacity={0.72} />
        </LinearGradient>
      </Defs>
      {[0, 5, 10, 15, 20].map((v) => (
        <SvgText key={`y${v}`} x={padL - 8} y={y(v) + 4} textAnchor="end" fill={C.muted} fontSize={10}>{v}</SvgText>
      ))}
      {data.map((d, i) => {
        const bw = 22;
        const x = padL + i * step + (step - bw) / 2;
        return (
          <Rect key={`b${i}`} x={x} y={y(d.trades)} width={bw} height={padT + plotH - y(d.trades)} rx={4} fill="url(#canaryBarGrad)" opacity={barOpacity} />
        );
      })}
      <Polyline points={points} fill="none" stroke={ACCENT} strokeWidth={2.5} strokeLinejoin="round" opacity={lineOpacity} />
      {data.map((d, i) => (
        <Circle key={`d${i}`} cx={padL + i * step + step / 2} cy={y(d.anomalies)} r={4} fill={ACCENT} opacity={lineOpacity} />
      ))}
      {data.map((d, i) => (
        <SvgText key={`x${i}`} x={padL + i * step + step / 2} y={H - 6} textAnchor="middle" fill={C.muted} fontSize={11}>{d.month}</SvgText>
      ))}
    </Svg>
  );
}
