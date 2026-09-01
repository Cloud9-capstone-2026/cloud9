import React from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ResultBody } from '../components/FlowOverlay';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

export function UploadDoneScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { upFile } = useAppState();
  const fileName = upFile?.name || 'trades_august_2026.csv';

  return (
    <ResultBody
      success
      title="업로드 완료!"
      body={`${fileName} 업로드를 완료했어요.\n지금 바로 분석할 수 있습니다.`}
      ctaLabel="분석 시작하기"
      onCta={() => navigation.replace('Analyzing')}
    />
  );
}
