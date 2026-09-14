import React, { useEffect, useRef } from 'react';
import { BackHandler } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ProgressBody } from '../components/FlowOverlay';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

export function UploadingScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { upFile, uploadFile } = useAppState();
  const fileName = upFile?.name || 'trades_august_2026.csv';
  const startedRef = useRef(false);

  // 업로드 요청이 나간 뒤부터는 이 화면에서 하드웨어 뒤로가기로 이탈할 수 없다 —
  // 서버는 이미 요청을 받고 있는 중이라, 나가버리면 결과를 확인할 방법이 없어진다.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => true);
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (startedRef.current || !upFile) return;
    startedRef.current = true;
    (async () => {
      try {
        await uploadFile(upFile.uri, upFile.name, upFile.mimeType, upFile.webFile);
        navigation.replace('UploadDone');
      } catch {
        navigation.replace('UploadFail');
      }
    })();
  }, [upFile, uploadFile, navigation]);

  return (
    <ProgressBody
      title="업로드 중.."
      body={`${fileName} 업로드 중입니다.\n잠시만 기다려주세요.`}
    />
  );
}
