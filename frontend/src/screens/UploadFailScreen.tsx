import React from 'react';
import { ResultBody } from '../components/FlowOverlay';
import { goToTab } from '../navigation/navigationRef';

export function UploadFailScreen() {
  return (
    <ResultBody
      success={false}
      title="업로드 실패"
      body="파일을 다시 업로드 해주세요."
      ctaLabel="확인"
      onCta={() => goToTab('Home')}
    />
  );
}
