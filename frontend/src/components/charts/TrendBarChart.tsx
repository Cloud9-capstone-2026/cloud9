import React from 'react';
import Svg, { Rect, Text as SvgText } from 'react-native-svg';
import { C } from '../../theme/tokens';
import type { BiasTrendDatum } from '../../data/types';

export function TrendBarChart({
  data, dataKey, color,
}: {
  data: BiasTrendDatum[];
  dataKey: '처분효과' | '과잉확신' | '복권형선호' | '군집거래';
  color: string;
}) {
  const W = 168, H = 100, padL = 20, padB = 18, padT = 8;
  const plotH = H - padB - padT;
  const n = data.length;
  const step = (W - padL - 6) / n;
  const bw = Math.min(16, step - 6);
  const y = (v: number) => padT + plotH - (v / 100) * plotH;

  return (
    <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height={100}>
      {[0, 50, 100].map((v) => (
        <SvgText key={`y${v}`} x={padL - 5} y={y(v) + 3} textAnchor="end" fill={C.muted} fontSize={8}>{v}</SvgText>
      ))}
      {data.map((d, i) => {
        const x = padL + i * step + (step - bw) / 2;
        const value = d[dataKey];
        return (
          <Rect
            key={`b${i}`}
            x={x}
            y={y(value)}
            width={bw}
            height={padT + plotH - y(value)}
            rx={3}
            fill={color}
            opacity={i === n - 1 ? 1 : 0.22}
          />
        );
      })}
      {data.map((d, i) => (
        <SvgText
          key={`x${i}`}
          x={padL + i * step + step / 2}
          y={H - 5}
          textAnchor="middle"
          fill={C.muted}
          fontSize={9}
          opacity={i === n - 1 ? 1 : 0.6}
        >
          {d.date}
        </SvgText>
      ))}
    </Svg>
  );
}
