import React, { useEffect, useRef } from 'react';
import { BackHandler } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { ProgressBody } from '../components/FlowOverlay';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

const POLL_INTERVAL_MS = 1500;

export function AnalyzingScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { pendingUpload, pollJobStatus, clearPendingUpload } = useAppState();
  const stoppedRef = useRef(false);

  // 분석이 서버에서 끝나기 전까지는 이 화면을 벗어날 수 없다 — 원자성 원칙: 결과(성공/실패)를
  // 보기 전에 이탈하면 그 파일의 처리 결과를 앱이 다시는 추적할 수 없게 된다.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => true);
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (!pendingUpload) {
      // pendingUpload 없이 이 화면에 온 경우(비정상 진입) — 더 진행할 게 없으니 실패로 처리.
      navigation.replace('AnalyzeFail');
      return;
    }
    stoppedRef.current = false;

    const poll = async () => {
      if (stoppedRef.current) return;
      try {
        const job = await pollJobStatus(pendingUpload.jobId);
        if (stoppedRef.current) return;
        if (job.status === 'done') {
          stoppedRef.current = true;
          const uploadId = pendingUpload.uploadId;
          clearPendingUpload();
          navigation.replace('AnalyzeDone', { uploadId });
        } else if (job.status === 'failed') {
          stoppedRef.current = true;
          clearPendingUpload();
          navigation.replace('AnalyzeFail');
        } else {
          setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch {
        // 네트워크 일시 오류 — job 자체가 사라진 게 아니니 잠시 후 재시도.
        if (!stoppedRef.current) setTimeout(poll, POLL_INTERVAL_MS);
      }
    };
    poll();

    return () => { stoppedRef.current = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingUpload?.jobId]);

  return (
    <ProgressBody
      title="거래 분석 중.."
      body={'AI가 매매 패턴을 정밀 분석하고 있어요.\n규칙 기반 탐지부터 딥러닝 판별까지 진행 중이에요.'}
    />
  );
}
