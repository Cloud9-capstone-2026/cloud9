import React from 'react';
import { ResultBody } from '../components/FlowOverlay';
import { goToTab } from '../navigation/navigationRef';

export function AnalyzeDoneScreen() {
  return (
    <ResultBody
      success
      title="분석 완료!"
      body={'총 18건의 분석을 완료했어요.\n리포트에서 자세한 분석 결과를 확인해보세요.'}
      ctaLabel="결과 보기"
      onCta={() => goToTab('ReportList')}
    />
  );
}
