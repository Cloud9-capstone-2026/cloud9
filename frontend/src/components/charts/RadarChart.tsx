import React from 'react';
import Svg, { Polygon, Line, Circle, Text as SvgText } from 'react-native-svg';
import { C } from '../../theme/tokens';

export interface RadarSeries {
  values: number[];
  color: string;
  fillOpacity: number;
  width?: number;
}

export function RadarChart({
  axes, series, size, radius, max, fontSize, height, dots,
}: {
  axes: string[];
  series: RadarSeries[];
  size: number;
  radius: number;
  max: number;
  fontSize: number;
  height: number;
  dots?: boolean;
}) {
  const cx = size / 2, cy = size / 2, R = radius, n = axes.length;
  const pt = (i: number, frac: number): [number, number] => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    return [cx + R * frac * Math.cos(a), cy + R * frac * Math.sin(a)];
  };

  return (
    <Svg viewBox={`0 0 ${size} ${size}`} width="100%" height={height}>
      {[0.25, 0.5, 0.75, 1].map((f, gi) => (
        <Polygon
          key={`g${gi}`}
          points={axes.map((_, i) => pt(i, f).join(',')).join(' ')}
          fill="none"
          stroke={C.border}
          strokeWidth={1}
        />
      ))}
      {axes.map((_, i) => {
        const [x, y] = pt(i, 1);
        return <Line key={`s${i}`} x1={cx} y1={cy} x2={x} y2={y} stroke={C.border} strokeWidth={1} />;
      })}
      {series.map((s, si) => (
        <Polygon
          key={`p${si}`}
          points={s.values.map((v, i) => pt(i, Math.max(v, 0) / max).join(',')).join(' ')}
          fill={s.color}
          fillOpacity={s.fillOpacity}
          stroke={s.color}
          strokeWidth={s.width || 2}
        />
      ))}
      {dots &&
        series[0].values.map((v, i) => {
          const [x, y] = pt(i, Math.max(v, 0) / max);
          return <Circle key={`dt${i}`} cx={x} cy={y} r={2} fill={series[0].color} />;
        })}
      {axes.map((a, i) => {
        const [x, y] = pt(i, 1.22);
        return (
          <SvgText key={`l${i}`} x={x} y={y + 3} textAnchor="middle" fill={C.muted} fontSize={fontSize}>{a}</SvgText>
        );
      })}
    </Svg>
  );
}
