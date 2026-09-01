import React from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ResultBody } from '../components/FlowOverlay';
import type { RootStackParamList } from '../navigation/types';

export function AnalyzeFailScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  return (
    <ResultBody
      success={false}
      title="분석 실패"
      body={'분석 중 문제가 생겼어요.\n잠시 후 다시 시도해주세요.'}
      ctaLabel="확인"
      onCta={() => navigation.navigate('Upload')}
    />
  );
}
