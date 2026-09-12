import React, { useEffect, useRef, useState } from 'react';
import Svg, { Rect, Text as SvgText, Defs, LinearGradient, Stop } from 'react-native-svg';
import { C } from '../../theme/tokens';

// 이 차트의 고정 렌더 높이 — 카드가 빈 상태일 때 크기를 유지해야 하면 이 값을 그대로 재사용할 것.
export const MONTHLY_CHART_HEIGHT = 158;

const ANIM_MS = 600;

function useGrowProgress(dep: unknown) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  useEffect(() => {
    setProgress(0);
    const startedAt = Date.now();
    const step = () => {
      const t = Math.min(1, (Date.now() - startedAt) / ANIM_MS);
      // ease-out
      setProgress(1 - Math.pow(1 - t, 3));
      if (t < 1) rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => { if (rafRef.current != null) cancelAnimationFrame(rafRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);
  return progress;
}

// 월별 거래내역 — 막대가 아래에서 위로 자라나는 모션. Y축은 이 차트 자신의 최댓값(6개월 중)을
// 4등분해서 눈금을 매긴다(다른 차트와 스케일을 공유하지 않음).
export function MonthlyBarChart({ months, values }: { months: string[]; values: number[] }) {
  const progress = useGrowProgress(values.join(','));
  const W = 356, H = MONTHLY_CHART_HEIGHT, padL = 26, padB = 24, padT = 8;
  const plotH = H - padB - padT;
  const n = months.length;
  const step = n > 0 ? (W - padL - 8) / n : 0;
  const maxV = Math.max(1, ...values);
  const ticks = [0, maxV / 4, maxV / 2, (maxV * 3) / 4, maxV];
  const y = (v: number) => padT + plotH - (v / maxV) * plotH;

  return (
    <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
      <Defs>
        <LinearGradient id="canaryBarGrad" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0%" stopColor="#1d4ed8" />
          <Stop offset="72%" stopColor="#1d4ed8" />
          <Stop offset="100%" stopColor="#3b82f6" stopOpacity={0.72} />
        </LinearGradient>
      </Defs>
      {ticks.map((v, i) => (
        <SvgText key={`y${i}`} x={padL - 8} y={y(v) + 4} textAnchor="end" fill={C.muted} fontSize={10}>{Math.round(v)}</SvgText>
      ))}
      {values.map((v, i) => {
        const bw = 22;
        const x = padL + i * step + (step - bw) / 2;
        const fullTop = y(v);
        const fullH = padT + plotH - fullTop;
        const animH = fullH * progress;
        return (
          <Rect key={`b${i}`} x={x} y={padT + plotH - animH} width={bw} height={animH} rx={4} fill="url(#canaryBarGrad)" />
        );
      })}
      {months.map((m, i) => (
        <SvgText key={`x${i}`} x={padL + i * step + step / 2} y={H - 6} textAnchor="middle" fill={C.muted} fontSize={11}>{m}</SvgText>
      ))}
    </Svg>
  );
}
