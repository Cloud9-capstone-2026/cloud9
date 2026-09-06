import React, { useEffect } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { RuleCardList, rulesAllValid } from '../components/RuleCardList';
import { C, text } from '../theme/tokens';
import { useAppState } from '../state/AppState';

export function RulesSettingsScreen() {
  const navigation = useNavigation();
  const { ruleOn, ruleVal, ruleMoney, ruleSnap, ruleRevert } = useAppState();

  useEffect(() => {
    ruleSnap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const valid = rulesAllValid(ruleOn, ruleVal, ruleMoney);

  const onBack = () => { ruleRevert(); navigation.goBack(); };
  const onSave = () => navigation.goBack();

  return (
    <Screen
      back
      onBackPress={onBack}
      floatingFooter={
        <Pressable
          onPress={onSave}
          disabled={!valid}
          style={[styles.saveBtn, { backgroundColor: valid ? C.blue : C.card }]}
        >
          <Text style={{ color: valid ? '#fff' : C.muted, fontSize: 17, fontWeight: '600' }}>저장하기</Text>
        </Pressable>
      }
    >
      <Text style={text.screenTitle}>탐지 규칙 설정</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>켜둔 규칙과 기준값으로 이상거래를 판정해요</Text>
      <View style={{ marginTop: 20 }}>
        <RuleCardList showBanner />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  subtitle: { marginTop: 3 },
  saveBtn: { borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
});
