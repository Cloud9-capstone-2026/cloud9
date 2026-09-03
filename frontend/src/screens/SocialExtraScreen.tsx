import React, { useState } from 'react';
import { View } from 'react-native';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, CtaButton, AuthTitle, AuthSubtitle, FIELD_GAP } from '../components/AuthField';
import { TermsAgreement } from '../components/TermsAgreement';
import { useAppState } from '../state/AppState';

export function SocialExtraScreen() {
  const { enterMainDirectly } = useAppState();
  const [name, setName] = useState('');
  const [terms, setTerms] = useState([false, false, false, false]);

  const allTerms = terms.every(Boolean);
  const toggleTerm = (i: number) => setTerms((prev) => prev.map((v, idx) => (idx === i ? !v : v)));
  const toggleAll = () => setTerms((prev) => (allTerms ? prev.map(() => false) : prev.map(() => true)));
  const canSubmit = name.trim().length > 0 && terms[0] && terms[1] && terms[2];

  return (
    <AuthScreen back>
      <AuthTitle>거의 다 됐어요</AuthTitle>
      <AuthSubtitle>닉네임과 약관 동의만 남았어요</AuthSubtitle>

      <View style={{ marginTop: 32, gap: FIELD_GAP }}>
        <AuthInput label="닉네임" value={name} onChangeText={setName} placeholder="앱에서 사용할 이름" />

        <TermsAgreement terms={terms} onToggleTerm={toggleTerm} onToggleAll={toggleAll} />
      </View>

      <View style={{ marginTop: 'auto', paddingTop: FIELD_GAP }}>
        <CtaButton label="시작하기" active={canSubmit} onPress={enterMainDirectly} />
      </View>
    </AuthScreen>
  );
}
