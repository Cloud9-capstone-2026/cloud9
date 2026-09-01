import React, { useEffect } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ProgressBody } from '../components/FlowOverlay';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

export function UploadingScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { upFile } = useAppState();
  const fileName = upFile?.name || 'trades_august_2026.csv';

  useEffect(() => {
    const t = setTimeout(() => navigation.replace('UploadDone'), 1800);
    return () => clearTimeout(t);
  }, [navigation]);

  return (
    <ProgressBody
      title="업로드 중.."
      body={`${fileName} 업로드 중입니다.\n잠시만 기다려주세요.`}
    />
  );
}
