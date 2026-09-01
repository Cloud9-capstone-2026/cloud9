import React from 'react';
import Svg, { Line, Circle, Text as SvgText } from 'react-native-svg';
import { ACCENT } from '../../theme/tokens';
import type { BiasComparisonDatum } from '../../data/types';

const LABEL_X = 76;
const RIGHT_X = 352;
const ROW_H = 32;
const PAD_T = 4;

export function DumbbellChart({ data, empty }: { data: BiasComparisonDatum[]; empty?: boolean }) {
  const W = 360;
  const H = data.length * ROW_H + PAD_T * 2;
  const x = (v: number) => LABEL_X + (v / 100) * (RIGHT_X - LABEL_X);

  return (
    <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="xMinYMin meet">
      {data.map((d, i) => {
        const cy = PAD_T + i * ROW_H + ROW_H / 2;
        return (
          <React.Fragment key={d.subject}>
            <Line x1={LABEL_X} y1={cy} x2={RIGHT_X} y2={cy} stroke="#dbe3ec" strokeWidth={1} />
            <SvgText x={0} y={cy + 4} fontSize={13} fill="#16213b">{d.subject}</SvgText>
            {!empty && (
              <>
                <Line x1={x(d.self)} y1={cy} x2={x(d.trading)} y2={cy} stroke={ACCENT} strokeWidth={2.5} strokeLinecap="round" />
                <Circle cx={x(d.trading)} cy={cy} r={4.5} fill="#64748b" stroke="#fff" strokeWidth={1.6} />
                <Circle cx={x(d.self)} cy={cy} r={4.5} fill={ACCENT} stroke="#fff" strokeWidth={1.6} />
              </>
            )}
          </React.Fragment>
        );
      })}
    </Svg>
  );
}
