import React, { useMemo, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useRoute, useNavigation, RouteProp } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { GradientCard } from '../components/GradientCard';
import { StatusBadge } from '../components/StatusBadge';
import { C, EMOTIONS, ACCENT, riskLevel } from '../theme/tokens';
import { tradesRaw } from '../data/mock';
import { useAppState } from '../state/AppState';
import { goToReportDetail } from '../navigation/navigationRef';
import type { RootStackParamList } from '../navigation/types';

export function JournalWriteScreen() {
  const route = useRoute<RouteProp<RootStackParamList, 'JournalWrite'>>();
  const navigation = useNavigation();
  const { journals, saveJournal } = useAppState();
  const { journalId } = route.params;

  const existing = journalId ? journals.find((j) => j.id === journalId) : null;
  const trade = useMemo(
    () => (existing ? tradesRaw.find((t) => t.stock === existing.stock) || tradesRaw[0] : tradesRaw[0]),
    [existing]
  );

  const [reason, setReason] = useState(existing?.reason ?? '');
  const [emotion, setEmotion] = useState(existing?.emotion ?? '');
  const [review, setReview] = useState(existing?.review ?? '');

  const filled = reason.trim().length > 0 && emotion.length > 0 && review.trim().length > 0;
  const isBuy = trade.type === 'buy';

  const handleSave = () => {
    saveJournal(journalId, { reason, emotion, review });
    navigation.goBack();
  };

  return (
    <Screen back contentStyle={styles.content}>
      <Text style={styles.title}>일지 작성</Text>

      <GradientCard colors={['#f8fbff', '#ffffff']}>
        <View style={styles.tradeRow}>
          <View>
            <Text style={styles.tradeStock}>{trade.stock}</Text>
            <View style={styles.tradeMetaRow}>
              <Text style={styles.tradeDate}>{trade.date}</Text>
              <Text style={[styles.tradeType, { color: isBuy ? C.red : C.blue }]}>{isBuy ? '매수' : '매도'}</Text>
            </View>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={styles.tradeAmount}>{trade.amount}원</Text>
            <StatusBadge risk={riskLevel(trade.score)} />
          </View>
        </View>
        <View style={styles.reportLinkRow}>
          <Pressable onPress={() => goToReportDetail(trade.id)}>
            <Text style={styles.reportLink}>분석 리포트 보기 →</Text>
          </Pressable>
        </View>
      </GradientCard>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>매매 이유</Text>
        <TextInput
          value={reason}
          onChangeText={setReason}
          placeholder="이 거래를 한 이유를 작성하세요..."
          placeholderTextColor={C.muted}
          style={styles.textarea}
          multiline
        />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>당시 감정</Text>
        <View style={styles.chipsRow}>
          {EMOTIONS.map((e) => {
            const selected = emotion === e;
            return (
              <Pressable
                key={e}
                onPress={() => setEmotion(selected ? '' : e)}
                style={[styles.emotionChip, { backgroundColor: selected ? ACCENT : C.mutedBg }]}
              >
                <Text style={{ fontSize: 12, color: selected ? '#fff' : C.muted, fontWeight: selected ? '500' : '400' }}>
                  #{e}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>복기 · 사후 회고</Text>
        <TextInput
          value={review}
          onChangeText={setReview}
          placeholder="지금 돌아보면 이 거래는 어땠나요?"
          placeholderTextColor={C.muted}
          style={styles.textarea}
          multiline
        />
      </View>

      <View style={styles.saveWrap}>
        <Pressable
          onPress={handleSave}
          style={[styles.saveBtn, { backgroundColor: filled ? C.blue : C.card }]}
        >
          <Text style={{ color: filled ? '#fff' : C.muted, fontSize: 15, fontWeight: '500' }}>저장하기</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 16, paddingBottom: 130 },
  title: { fontSize: 18, fontWeight: '600', color: C.navy, letterSpacing: -0.2 },
  tradeRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  tradeStock: { fontSize: 16, fontWeight: '600', color: C.navy, marginBottom: 4, letterSpacing: -0.2 },
  tradeMetaRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  tradeDate: { fontSize: 12, color: C.muted },
  tradeType: { fontSize: 12, fontWeight: '500' },
  tradeAmount: { fontSize: 14, fontWeight: '500', color: C.navy, marginBottom: 5 },
  reportLinkRow: { marginTop: 12, borderTopWidth: 1, borderTopColor: C.border, paddingTop: 10, alignItems: 'flex-end' },
  reportLink: { fontSize: 12, fontWeight: '500', color: C.blue },
  card: { backgroundColor: C.card, borderRadius: 30, padding: 16 },
  cardTitle: { fontSize: 13, fontWeight: '500', color: C.navy, marginBottom: 10 },
  textarea: {
    minHeight: 80, padding: 12, backgroundColor: C.mutedBg, borderRadius: 20,
    fontSize: 13, color: C.navy, textAlignVertical: 'top', lineHeight: 21,
  },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  emotionChip: { borderRadius: 999, paddingVertical: 7, paddingHorizontal: 13 },
  saveWrap: { paddingTop: 4 },
  saveBtn: {
    borderRadius: 999, paddingVertical: 15, alignItems: 'center',
    shadowColor: '#16213b', shadowOpacity: 0.1, shadowOffset: { width: 0, height: 4 }, shadowRadius: 18, elevation: 6,
  },
});
