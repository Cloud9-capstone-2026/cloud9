import React from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ResultBody } from '../components/FlowOverlay';
import type { RootStackParamList } from '../navigation/types';

export function UploadFailScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  return (
    <ResultBody
      success={false}
      title="업로드 실패"
      body="파일을 다시 업로드 해주세요."
      ctaLabel="확인"
      onCta={() => navigation.goBack()}
    />
  );
}
