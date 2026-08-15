import React from 'react';
import Svg, { Circle, Text as SvgText } from 'react-native-svg';
import { C, LAYER_RING } from '../../theme/tokens';

export function LayerRing({ score, triggered, failed }: { score: number; triggered: boolean; failed: boolean }) {
  const r = 34, cx = 44, cy = 44, circ = 2 * Math.PI * r;
  const color = triggered ? LAYER_RING.detected : LAYER_RING.undetected;
  return (
    <Svg width={88} height={88} viewBox="0 0 88 88">
      <Circle cx={cx} cy={cy} r={r} fill="none" stroke={C.mutedBg} strokeWidth={7} />
      {!failed && (
        <Circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={7}
          strokeDasharray={`${(circ * score) / 100} ${circ}`}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      )}
      <SvgText
        x={cx}
        y={cy + 5}
        textAnchor="middle"
        fill={failed ? LAYER_RING.undetected : color}
        fontSize={failed ? 18 : 14}
        fontWeight="700"
      >
        {failed ? '−' : score}
      </SvgText>
    </Svg>
  );
}
