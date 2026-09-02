import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { FieldLabel } from './AuthField';
import { IconTick } from '../assets/icons';
import { C } from '../theme/tokens';
import type { AuthStackParamList } from '../navigation/types';

const TERMS_ROWS = [
  { label: '(필수) 서비스 이용약관 동의', legal: 'terms' as const },
  { label: '(필수) 개인정보 수집·이용 동의', legal: 'privacy' as const },
  { label: '(필수) 만 14세 이상입니다', legal: null },
  { label: '(선택) 마케팅 정보 수신 동의', legal: null },
];

export function TermsAgreement({
  terms, onToggleTerm, onToggleAll,
}: {
  terms: boolean[];
  onToggleTerm: (i: number) => void;
  onToggleAll: () => void;
}) {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const allTerms = terms.every(Boolean);

  return (
    <View>
      <FieldLabel>약관 동의</FieldLabel>
      <View style={styles.termsCard}>
        <View style={styles.termsHead}>
          <Text style={styles.termsHeadLabel}>전체 동의</Text>
          <Pressable onPress={onToggleAll} style={[styles.roundCheck, allTerms && styles.roundCheckOn]}>
            {allTerms && <IconTick size={11} />}
          </Pressable>
        </View>
        {TERMS_ROWS.map((row, i) => (
          <View key={row.label} style={[styles.termRow, i > 0 && styles.termDivider]}>
            <Pressable onPress={() => onToggleTerm(i)} style={styles.termLeft}>
              <View style={[styles.termCheck, terms[i] && styles.termCheckOn]}>
                {terms[i] && <IconTick size={10} />}
              </View>
              <Text style={styles.termLabel}>{row.label}</Text>
            </Pressable>
            {row.legal && (
              <Pressable onPress={() => navigation.navigate('Legal', { kind: row.legal!, variant: 'auth' })}>
                <Text style={styles.termView}>보기</Text>
              </Pressable>
            )}
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  termsCard: { backgroundColor: '#fff', borderRadius: 20, paddingVertical: 14, paddingHorizontal: 16 },
  termsHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 10 },
  termsHeadLabel: { fontSize: 15, fontWeight: '600', color: C.navy },
  roundCheck: { width: 17, height: 17, borderRadius: 9, backgroundColor: '#f1f5f9', alignItems: 'center', justifyContent: 'center' },
  roundCheckOn: { backgroundColor: C.blue, borderColor: C.blue },
  termRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 11 },
  termDivider: { borderTopWidth: 1, borderTopColor: C.border },
  termLeft: { flexDirection: 'row', alignItems: 'center', gap: 9, flex: 1 },
  termCheck: { width: 18, height: 18, borderRadius: 9, backgroundColor: '#f1f5f9', alignItems: 'center', justifyContent: 'center' },
  termCheckOn: { backgroundColor: C.blue },
  termLabel: { fontSize: 15, color: C.navy },
  termView: { fontSize: 12, color: '#cbd5e1', textDecorationLine: 'underline' },
});
