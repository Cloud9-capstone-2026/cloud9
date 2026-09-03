import React, { useEffect } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { RuleCardList, rulesAllValid } from '../components/RuleCardList';
import { IconBack } from '../assets/icons';
import { C, shadow } from '../theme/tokens';
import { useAppState } from '../state/AppState';

export function RulesSettingsScreen() {
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();
  const { ruleOn, ruleVal, ruleMoney, ruleSnap, ruleRevert } = useAppState();

  useEffect(() => {
    ruleSnap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const valid = rulesAllValid(ruleOn, ruleVal, ruleMoney);

  const onBack = () => { ruleRevert(); navigation.goBack(); };
  const onSave = () => navigation.goBack();

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: (insets.top || 0) + 12 }]}>
        <Pressable onPress={onBack} style={[styles.backBtn, shadow.header]}>
          <IconBack size={20} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>탐지 규칙 설정</Text>
        <Text style={styles.subtitle}>켜둔 규칙과 기준값으로 이상거래를 판정해요</Text>
        <View style={{ marginTop: 20 }}>
          <RuleCardList showBanner />
        </View>
      </ScrollView>
      <View style={[styles.footer, { paddingBottom: Math.max(16, insets.bottom) + 8 }]}>
        <Pressable
          onPress={onSave}
          disabled={!valid}
          style={[styles.saveBtn, { backgroundColor: valid ? C.blue : C.card }]}
        >
          <Text style={{ color: valid ? '#fff' : C.muted, fontSize: 17, fontWeight: '600' }}>저장하기</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { paddingHorizontal: 22, paddingBottom: 10 },
  backBtn: { backgroundColor: C.card, alignSelf: 'flex-start', padding: 8, borderRadius: 20 },
  content: { paddingHorizontal: 22, paddingBottom: 110 },
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 14, color: C.muted, marginTop: 12, lineHeight: 20 },
  footer: { position: 'absolute', left: 22, right: 22, bottom: 0 },
  saveBtn: { borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
});
