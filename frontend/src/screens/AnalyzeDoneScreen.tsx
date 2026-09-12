import React, { useEffect, useState } from 'react';
import { useRoute, RouteProp } from '@react-navigation/native';
import { ResultBody } from '../components/FlowOverlay';
import { goToTab } from '../navigation/navigationRef';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

export function AnalyzeDoneScreen() {
  const route = useRoute<RouteProp<RootStackParamList, 'AnalyzeDone'>>();
  const { getUploads } = useAppState();
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    const uploadId = route.params?.uploadId;
    if (uploadId == null) return;
    let cancelled = false;
    (async () => {
      try {
        const uploads = await getUploads(50, 0);
        const match = uploads.find((u) => u.id === uploadId);
        if (!cancelled && match) setCount(match.row_count);
      } catch {
        // 건수 조회 실패해도 완료 화면 자체는 그대로 보여줌 — 문구만 일반화됨.
      }
    })();
    return () => { cancelled = true; };
  }, [route.params?.uploadId, getUploads]);

  return (
    <ResultBody
      success
      title="분석 완료!"
      body={count != null
        ? `총 ${count}건의 분석을 완료했어요.\n리포트에서 자세한 분석 결과를 확인해보세요.`
        : '분석을 완료했어요.\n리포트에서 자세한 분석 결과를 확인해보세요.'}
      ctaLabel="결과 보기"
      onCta={() => goToTab('ReportList')}
    />
  );
}
