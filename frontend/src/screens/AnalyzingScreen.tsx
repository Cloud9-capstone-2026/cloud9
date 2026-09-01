import React, { useEffect } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ProgressBody } from '../components/FlowOverlay';
import type { RootStackParamList } from '../navigation/types';

export function AnalyzingScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  useEffect(() => {
    const t = setTimeout(() => navigation.replace('AnalyzeDone'), 3600);
    return () => clearTimeout(t);
  }, [navigation]);

  return (
    <ProgressBody
      title="거래 분석 중.."
      body={'AI가 매매 패턴을 정밀 분석하고 있어요.\n규칙 기반 탐지부터 딥러닝 판별까지 진행 중이에요.'}
    />
  );
}
