import React from 'react';
import { ConfirmModal } from './ConfirmModal';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';

export function NotifPermissionModal() {
  const { notifPermModalOpen, requestNotifPermission, closeNotifPermModal } = useAppState();

  return (
    <ConfirmModal
      visible={notifPermModalOpen}
      title="알림을 허용하시겠습니까?"
      body={'거래 분석 완료, 업로드 상태 등\n서비스 이용에 필요한 알림을 보내드립니다.'}
      confirmLabel="허용"
      confirmColor={C.blue}
      cancelLabel="나중에"
      onConfirm={() => requestNotifPermission(true)}
      onCancel={() => requestNotifPermission(false)}
    />
  );
}
