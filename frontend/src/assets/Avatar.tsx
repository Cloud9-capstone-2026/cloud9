import React from 'react';
import Svg, { Path, Ellipse, Circle } from 'react-native-svg';

export function Avatar({ size = 100 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 140 140">
      <Path
        d="M70 14c22-2 40 16 36 36 10 8 8 26-6 32 2 16-16 28-30 20-14 12-32 2-32-14-16-2-22-20-10-32-6-18 10-34 28-34 4-6 10-8 14-8z"
        fill="#f0955a"
      />
      <Ellipse cx={52} cy={58} rx={15} ry={18} fill="#fff" />
      <Circle cx={49} cy={54} r={7.8} fill="#111" />
      <Ellipse cx={88} cy={62} rx={10} ry={12} fill="#fff" />
      <Circle cx={92} cy={65} r={5.2} fill="#111" />
      <Path d="M60 82c4 6 12 6 16 0" stroke="#111" strokeWidth={3} fill="none" strokeLinecap="round" />
      <Ellipse cx={102} cy={42} rx={5} ry={8} fill="#5aa9e6" />
    </Svg>
  );
}
