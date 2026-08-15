import React from 'react';
import Svg, { Circle, Text as SvgText } from 'react-native-svg';
import { C } from '../../theme/tokens';

export function RingChart({
  danger, caution, safe, dangerColor, cautionColor, safeColor,
}: {
  danger: number; caution: number; safe: number;
  dangerColor: string; cautionColor: string; safeColor: string;
}) {
  const total = Math.max(1, danger + caution + safe);
  const r = 36, cx = 46, cy = 52, circ = 2 * Math.PI * r, gap = 4;

  const seg = (value: number, color: string, rot: number, key: string) => (
    <Circle
      key={key}
      cx={cx}
      cy={cy}
      r={r}
      fill="none"
      stroke={color}
      strokeWidth={8}
      strokeDasharray={`${Math.max(0, (value / total) * circ - gap)} ${circ}`}
      transform={`rotate(${rot} ${cx} ${cy})`}
    />
  );

  return (
    <Svg width={92} height={104}>
      <Circle cx={cx} cy={cy} r={r} fill="none" stroke={C.mutedBg} strokeWidth={8} />
      {seg(danger, dangerColor, -90, 'danger')}
      {seg(caution, cautionColor, (danger / total) * 360 - 90, 'caution')}
      {seg(safe, safeColor, ((danger + caution) / total) * 360 - 90, 'safe')}
      <SvgText x={cx} y={cx + 2} textAnchor="middle" fill={C.muted} fontSize={8}>Total</SvgText>
      <SvgText x={cx} y={cx + 16} textAnchor="middle" fill={C.navy} fontSize={16} fontWeight="600">{total}</SvgText>
    </Svg>
  );
}
