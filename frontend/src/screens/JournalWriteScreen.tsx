import React, { useMemo, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useRoute, useNavigation, RouteProp } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { GradientCard } from '../components/GradientCard';
import { StatusBadge } from '../components/StatusBadge';
import { ConfirmModal } from '../components/ConfirmModal';
import { C, EMOTIONS, ACCENT, riskLevel, shadow, text } from '../theme/tokens';
import { tradesRaw } from '../data/mock';
import { useAppState } from '../state/AppState';
import { goToReportDetail } from '../navigation/navigationRef';
import type { RootStackParamList } from '../navigation/types';

// 10개를 5개씩 2줄로 고정 배치 — flexWrap에 맡기면 칩 너비가 제각각이라 줄마다 개수가
// 들쭉날쭉해지는 문제가 있어서, 줄을 직접 나누고 각 줄 안에서 flex:1로 균등폭을 줌.
const EMOTION_ROWS = [EMOTIONS.slice(0, 5), EMOTIONS.slice(5)];

export function JournalWriteScreen() {
  const route = useRoute<RouteProp<RootStackParamList, 'JournalWrite'>>();
  const navigation = useNavigation();
  const { journals, saveJournal, addJournal, deleteJournal } = useAppState();
  const { journalId, tradeId } = route.params;

  const existing = journalId ? journals.find((j) => j.id === journalId) : null;
  const trade = useMemo(() => {
    if (existing) return tradesRaw.find((t) => t.stock === existing.stock) || tradesRaw[0];
    if (tradeId != null) return tradesRaw.find((t) => t.id === tradeId) || tradesRaw[0];
    return tradesRaw[0];
  }, [existing, tradeId]);

  const [reason, setReason] = useState(existing?.reason ?? '');
  const [emotion, setEmotion] = useState(existing?.emotion ?? '');
  const [review, setReview] = useState(existing?.review ?? '');
  // 이미 작성된 일지를 볼 때는 "수정하기"를 눌러야만 편집 가능하게 잠가둠(새로 작성할 땐 처음부터 편집 가능).
  const [locked, setLocked] = useState(!!existing);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const filled = reason.trim().length > 0 && emotion.length > 0 && review.trim().length > 0;
  const isBuy = trade.type === 'buy';

  const handleSave = () => {
    if (journalId != null) {
      saveJournal(journalId, { reason, emotion, review });
    } else {
      addJournal({
        id: trade.id,
        stock: trade.stock,
        date: trade.date,
        type: trade.type,
        emotion,
        risk: riskLevel(trade.score),
        memo: reason.slice(0, 40),
        reason,
        review,
      });
    }
    navigation.goBack();
  };

  const handleDelete = () => {
    if (existing) deleteJournal(existing.id);
    setDeleteOpen(false);
    navigation.goBack();
  };

  return (
    <Screen
      back
      contentStyle={styles.content}
      floatingFooter={
        locked ? (
          <View style={styles.footerRow}>
            <Pressable onPress={() => setLocked(false)} style={[styles.halfBtn, styles.editBtn]}>
              <Text style={styles.editBtnText}>수정하기</Text>
            </Pressable>
            <Pressable onPress={() => setDeleteOpen(true)} style={[styles.halfBtn, styles.deleteBtn]}>
              <Text style={styles.deleteBtnText}>삭제하기</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            onPress={handleSave}
            disabled={!filled}
            style={[styles.saveBtn, { backgroundColor: filled ? C.blue : C.card }]}
          >
            <Text style={{ color: filled ? '#fff' : C.muted, fontSize: 17, fontWeight: '500' }}>저장하기</Text>
          </Pressable>
        )
      }
    >
      <Text style={text.screenTitle}>{existing ? '거래 일지' : '일지 작성'}</Text>

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

      <View>
        <Text style={styles.fieldLabel}>매매 이유</Text>
        <View style={styles.card}>
          {locked ? (
            <Text style={styles.textarea}>{reason}</Text>
          ) : (
            <TextInput
              value={reason}
              onChangeText={setReason}
              placeholder="이 거래를 한 이유를 작성하세요..."
              placeholderTextColor={C.muted}
              style={styles.textarea}
              multiline
            />
          )}
        </View>
      </View>

      <View>
        <Text style={styles.fieldLabel}>당시 감정</Text>
        <View style={styles.card}>
          <View style={styles.chipsCol}>
            {EMOTION_ROWS.map((row, ri) => (
              <View key={ri} style={styles.chipsRow}>
                {row.map((e) => {
                  const selected = emotion === e;
                  return (
                    <Pressable
                      key={e}
                      onPress={locked ? undefined : () => setEmotion(selected ? '' : e)}
                      style={[styles.emotionChip, { backgroundColor: selected ? ACCENT : C.mutedBg }]}
                    >
                      <Text
                        numberOfLines={1}
                        style={{ fontSize: 13, color: selected ? '#fff' : C.muted, fontWeight: selected ? '500' : '400' }}
                      >
                        #{e}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            ))}
          </View>
        </View>
      </View>

      <View>
        <Text style={styles.fieldLabel}>복기 · 사후 회고</Text>
        <View style={styles.card}>
          {locked ? (
            <Text style={styles.textarea}>{review}</Text>
          ) : (
            <TextInput
              value={review}
              onChangeText={setReview}
              placeholder="지금 돌아보면 이 거래는 어땠나요?"
              placeholderTextColor={C.muted}
              style={styles.textarea}
              multiline
            />
          )}
        </View>
      </View>

      <ConfirmModal
        visible={deleteOpen}
        title="일지를 삭제할까요?"
        body="삭제한 기록은 되돌릴 수 없어요."
        confirmLabel="삭제하기"
        confirmColor={C.red}
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 16 },
  tradeRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  tradeStock: { fontSize: 18, fontWeight: '600', color: C.navy, marginBottom: 4, letterSpacing: -0.2 },
  tradeMetaRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  tradeDate: { fontSize: 13, color: C.muted },
  tradeType: { fontSize: 13, fontWeight: '500' },
  tradeAmount: { fontSize: 16, fontWeight: '500', color: C.navy, marginBottom: 5 },
  reportLinkRow: { marginTop: 12, borderTopWidth: 1, borderTopColor: C.border, paddingTop: 10, alignItems: 'flex-end' },
  reportLink: { fontSize: 13, fontWeight: '500', color: C.blue },
  fieldLabel: { fontSize: 15, fontWeight: '500', color: C.navy, marginBottom: 10 },
  card: { backgroundColor: C.card, borderRadius: 30, padding: 16 },
  textarea: {
    minHeight: 100, padding: 12, backgroundColor: C.mutedBg, borderRadius: 20,
    fontSize: 15, color: C.navy, textAlignVertical: 'top', lineHeight: 21,
  },
  chipsCol: { gap: 8 },
  chipsRow: { flexDirection: 'row', gap: 8 },
  emotionChip: { flex: 1, borderRadius: 999, paddingVertical: 7, alignItems: 'center' },
  saveBtn: {
    borderRadius: 999, paddingVertical: 17, alignItems: 'center',
    ...shadow.floating,
  },
  footerRow: { flexDirection: 'row', gap: 10 },
  halfBtn: { flex: 1, borderRadius: 999, paddingVertical: 17, alignItems: 'center', ...shadow.floating },
  editBtn: { backgroundColor: C.card },
  editBtnText: { color: C.navy, fontSize: 17, fontWeight: '500' },
  deleteBtn: { backgroundColor: C.red },
  deleteBtnText: { color: '#fff', fontSize: 17, fontWeight: '500' },
});
