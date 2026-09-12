import React, { useEffect } from 'react';
import { BackHandler } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ResultBody } from '../components/FlowOverlay';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

export function UploadDoneScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { pendingUpload } = useAppState();
  const fileName = pendingUpload?.fileName || 'trades_august_2026.csv';

  // 분석은 서버에서 업로드 시점에 이미 시작됐음 — "분석 시작하기"는 화면 전환용 버튼일 뿐,
  // 그 전까지는 여기서도 이탈할 수 없게 막는다(업로드-분석 원자성).
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => true);
    return () => sub.remove();
  }, []);

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
