import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { RuleCardList, rulesAllValid } from '../components/RuleCardList';
import { IconBack } from '../assets/icons';
import { C, shadow } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { OnboardingStackParamList } from '../navigation/types';

export function TutRulesEditScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<OnboardingStackParamList>>();
  const insets = useSafeAreaInsets();
  const { ruleOn, ruleVal, ruleMoney, ruleRevert, setRulesConfirmed } = useAppState();

  const valid = rulesAllValid(ruleOn, ruleVal, ruleMoney);

  const onBack = () => { ruleRevert(); navigation.goBack(); };
  const onConfirm = () => { setRulesConfirmed(true); navigation.goBack(); };

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: (insets.top || 0) + 12 }]}>
        <Pressable onPress={onBack} style={[styles.backBtn, shadow.header]}>
          <IconBack size={20} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>나만의 위험 기준 정하기</Text>
        <Text style={styles.subtitle}>{'걱정되는 매매 습관만 켜두면, 그 기준 그대로 정확하게 잡아줘요.\n잘 모르겠으면 추천 값 그대로 둬도 괜찮아요.'}</Text>
        <View style={{ marginTop: 20 }}>
          <RuleCardList />
        </View>
      </ScrollView>
      <View style={[styles.footer, { paddingBottom: Math.max(16, insets.bottom) + 8 }]}>
        <Pressable
          onPress={onConfirm}
          disabled={!valid}
          style={[styles.confirmBtn, { backgroundColor: valid ? C.blue : '#e2e8f0' }]}
        >
          <Text style={{ color: valid ? '#fff' : '#a5b4c8', fontSize: 17, fontWeight: '600' }}>확인</Text>
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
  subtitle: { fontSize: 15, color: C.muted, marginTop: 6, lineHeight: 20 },
  footer: { position: 'absolute', left: 22, right: 22, bottom: 0 },
  confirmBtn: { borderRadius: 999, paddingVertical: 16, alignItems: 'center' },
});
