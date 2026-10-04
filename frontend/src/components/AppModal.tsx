import React from 'react';
import { Modal, View, Platform, StyleSheet } from 'react-native';
import { createPortal } from 'react-dom';
import { useModalRoot } from '../state/ModalRootContext';

// ConfirmModal/NotifDetailModal/BiasInfoModal이 공통으로 쓰는 모달 틀.
// 네이티브는 RN Modal 그대로(문제 없음). 웹은 ModalRootContext가 App.tsx의 폰 프레임
// 안에 마련해둔 자리로 직접 포털을 띄워서, 브라우저 창 전체가 아니라 그 프레임
// 크기 안에서만 모달이 뜨게 한다.
export function AppModal({
  visible, onRequestClose, children,
}: {
  visible: boolean;
  onRequestClose: () => void;
  children: React.ReactNode;
}) {
  const modalRootRef = useModalRoot();

  if (Platform.OS === 'web') {
    if (!visible) return null;
    const rootNode = modalRootRef?.current;
    if (!rootNode) return null;
    return createPortal(<View style={StyleSheet.absoluteFill}>{children}</View>, rootNode);
  }

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onRequestClose}>
      {children}
    </Modal>
  );
}
