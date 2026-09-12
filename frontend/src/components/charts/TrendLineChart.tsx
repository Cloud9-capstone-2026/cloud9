import React from 'react';
import Svg, { Line, Circle, Polyline, Text as SvgText } from 'react-native-svg';
import { C } from '../../theme/tokens';
import type { BiasTrendDatum } from '../../data/types';

export function TrendLineChart({
  data, dataKey, color, empty,
}: {
  data: BiasTrendDatum[];
  dataKey: '처분효과' | '과잉확신' | '복권형선호' | '군집거래';
  color: string;
  empty?: boolean;
}) {
  const W = 168, H = 100, padL = 20, padB = 18, padT = 8;
  const plotH = H - padB - padT;
  const n = data.length;
  const step = (W - padL - 6) / (n - 1 || 1);
  const y = (v: number) => padT + plotH - (v / 100) * plotH;
  const x = (i: number) => padL + i * step;

  return (
    <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height={100}>
      {[0, 50, 100].map((v) => (
        <React.Fragment key={`g${v}`}>
          <Line x1={padL} y1={y(v)} x2={W - 6} y2={y(v)} stroke="#eef2f7" strokeWidth={1} />
          <SvgText x={padL - 5} y={y(v) + 3} textAnchor="end" fill={C.muted} fontSize={8}>{v}</SvgText>
        </React.Fragment>
      ))}
      {!empty && (
        <Polyline
          // 값이 null인 달(그 이전엔 검사 이력 자체가 없음)은 선 연결에서 제외 —
          // 데이터가 있는 지점들끼리만 이어지고, 그 앞은 자연스럽게 빈 채로 남는다.
          points={data
            .map((d, i) => (d[dataKey] == null ? null : `${x(i)},${y(d[dataKey] as number)}`))
            .filter((p): p is string => p !== null)
            .join(' ')}
          fill="none"
          stroke={color}
          strokeWidth={1.6}
          strokeOpacity={0.55}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {!empty && data.map((d, i) => {
        const v = d[dataKey];
        if (v == null) return null;
        const isLatest = i === n - 1;
        return (
          <Circle
            key={`p${i}`}
            cx={x(i)}
            cy={y(v)}
            r={isLatest ? 3.2 : 2.4}
            fill={d.tested ? color : '#fff'}
            stroke={color}
            strokeWidth={1.4}
            opacity={isLatest ? 1 : 0.55}
          />
        );
      })}
      {data.map((d, i) => (
        <SvgText
          key={`x${i}`}
          x={x(i)}
          y={H - 4}
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
