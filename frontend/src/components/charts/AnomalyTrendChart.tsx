import React, { useEffect, useRef, useState } from 'react';
import Svg, { Polyline, Circle, Text as SvgText } from 'react-native-svg';
import { C, ACCENT } from '../../theme/tokens';
import { MONTHLY_CHART_HEIGHT } from './MonthlyBarChart';

const ANIM_MS = 700;

function useRevealProgress(dep: unknown) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  useEffect(() => {
    setProgress(0);
    const startedAt = Date.now();
    const step = () => {
      const t = Math.min(1, (Date.now() - startedAt) / ANIM_MS);
      setProgress(t);
      if (t < 1) rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => { if (rafRef.current != null) cancelAnimationFrame(rafRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);
  return progress;
}

// 이상 탐지 추이 — 점이 왼쪽에서 오른쪽으로 순서대로 이어지는 모션. Y축은 이 차트 자신의
// 최댓값(6개월 중)을 4등분(월별 거래내역 차트와 스케일 공유 안 함).
export function AnomalyTrendChart({ months, values }: { months: string[]; values: number[] }) {
  const progress = useRevealProgress(values.join(','));
  const W = 356, H = MONTHLY_CHART_HEIGHT, padL = 26, padB = 24, padT = 8;
  const plotH = H - padB - padT;
  const n = months.length;
  const step = n > 0 ? (W - padL - 8) / n : 0;
  const maxV = Math.max(1, ...values);
  const ticks = [0, maxV / 4, maxV / 2, (maxV * 3) / 4, maxV];
  const y = (v: number) => padT + plotH - (v / maxV) * plotH;
  const x = (i: number) => padL + i * step + step / 2;

  // n개 점을 순서대로 드러내되, 현재 구간 점은 이전 점 쪽으로 보간해서 자연스럽게 이어지게.
  const revealed = progress * (n - 1 || 1);
  const points = values
    .map((v, i) => {
      if (i > revealed) return null;
      const partial = i === Math.floor(revealed) && i < n - 1 ? revealed - i : 0;
      const vi = partial > 0 ? v + (values[i + 1] - v) * partial : v;
      const xi = partial > 0 ? x(i) + (x(i + 1) - x(i)) * partial : x(i);
      return `${xi},${y(vi)}`;
    })
    .filter((p): p is string => p !== null)
    .join(' ');

  return (
    <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
      {ticks.map((v, i) => (
        <SvgText key={`y${i}`} x={padL - 8} y={y(v) + 4} textAnchor="end" fill={C.muted} fontSize={10}>{Math.round(v)}</SvgText>
      ))}
      <Polyline points={points} fill="none" stroke={ACCENT} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
      {values.map((v, i) => (
        i <= revealed && <Circle key={`d${i}`} cx={x(i)} cy={y(v)} r={4} fill={ACCENT} />
      ))}
      {months.map((m, i) => (
        <SvgText key={`x${i}`} x={x(i)} y={H - 6} textAnchor="middle" fill={C.muted} fontSize={11}>{m}</SvgText>
      ))}
    </Svg>
  );
}
