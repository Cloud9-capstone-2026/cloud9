import React, { createContext, useContext, useRef } from 'react';
import { View, Platform, StyleSheet } from 'react-native';

// 웹에서 RN Modal은 document.body에 직접 포털을 띄워서, App.tsx가 폰 화면처럼 좁게
// 잡아둔 프레임을 무시하고 브라우저 창 전체를 덮어버린다(react-native-web/Modal/
// ModalPortal.js가 항상 document.body에 붙임 — 다른 대상을 지정할 방법이 없음).
// 그래서 웹에서는 이 프레임 안에 있는 오버레이 자리(아래 View)로 직접 포털을 띄우게
// 우리가 대신 관리한다. 네이티브(iOS/Android)는 애초에 화면 전체가 앱이라 이 문제가
// 없어서 그대로 RN Modal을 쓴다(components/AppModal.tsx 참고).
const ModalRootContext = createContext<React.RefObject<any> | null>(null);

export function ModalRootProvider({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<any>(null);
  return (
    <ModalRootContext.Provider value={rootRef}>
      {children}
      {Platform.OS === 'web' && (
        // eslint-disable-next-line react-native/no-deprecated-style-props -- 'box-none'은
        // 웹 변환 라이브러리(react-native-web)가 prop으로 줬을 때만 정확히 처리한다
        // (style 안에 넣으면 유효한 CSS 값이 아니라서 무시되고 기본값(auto)이 돼
        // 화면 전체 클릭을 가로채는 버그가 생김 — 실제로 겪어서 확인함).
        <View ref={rootRef} style={StyleSheet.absoluteFill} pointerEvents="box-none" />
      )}
    </ModalRootContext.Provider>
  );
}

export function useModalRoot() {
  return useContext(ModalRootContext);
}
