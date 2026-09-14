import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useRoute, useFocusEffect, useNavigation, RouteProp } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { GradientCard } from '../components/GradientCard';
import { StatusBadge } from '../components/StatusBadge';
import { Spinner } from '../components/FlowOverlay';
import { ConfirmModal } from '../components/ConfirmModal';
import { C, EMOTIONS, ACCENT, shadow, text } from '../theme/tokens';
import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import { formatDate } from '../utils/formatDate';
import { buildAnalysisLookup, findAnalysisForTrade, verdictToRisk } from '../utils/matchTradeAnalysis';
import { useAppState } from '../state/AppState';
import { goToReportDetail } from '../navigation/navigationRef';
import type { RootStackParamList } from '../navigation/types';

// 10개를 5개씩 2줄로 고정 배치 — flexWrap에 맡기면 칩 너비가 제각각이라 줄마다 개수가
// 들쭉날쭉해지는 문제가 있어서, 줄을 직접 나누고 각 줄 안에서 flex:1로 균등폭을 줌.
const EMOTION_ROWS = [EMOTIONS.slice(0, 5), EMOTIONS.slice(5)];

export function JournalWriteScreen() {
  const route = useRoute<RouteProp<RootStackParamList, 'JournalWrite'>>();
  const navigation = useNavigation();
  const { journals, refreshJournals, saveJournal, createJournalEntry, deleteJournal, getAllTrades, getAllAnalysis } = useAppState();
  const { journalId, tradeId } = route.params;

  const [trades, setTrades] = useState<TradeRaw[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const [tradesRes, analysisRes] = await Promise.all([getAllTrades(), getAllAnalysis()]);
          if (!cancelled) {
            setTrades(tradesRes);
            setAnalysis(analysisRes);
          }
        } catch {
          // 네트워크 실패 — 이전 값 유지
        }
      })();
      // 일지 목록은 별도 상태(AppState)라 실패해도 위 거래/분석 표시를 막으면 안 되므로 독립적으로 불러온다.
      refreshJournals().catch(() => {});
      return () => { cancelled = true; };
    }, [getAllTrades, getAllAnalysis, refreshJournals])
  );

  const existing = journalId ? journals.find((j) => j.id === journalId) : null;
  const resolvedTradeId = existing ? existing.trade_id : tradeId;
  const rawTrade = useMemo(
    () => trades.find((t) => t.id === resolvedTradeId),
    [trades, resolvedTradeId]
  );
  const analysisLookup = useMemo(() => buildAnalysisLookup(analysis), [analysis]);
  const matched = rawTrade ? findAnalysisForTrade(analysisLookup, rawTrade) : null;
  const risk = matched ? verdictToRisk(matched.detail.verdict) : null;

  const [reason, setReason] = useState(existing?.reason ?? '');
  const [emotion, setEmotion] = useState(existing?.emotion ?? '');
  const [review, setReview] = useState(existing?.review ?? '');
  // 이미 작성된 일지를 볼 때는 "수정하기"를 눌러야만 편집 가능하게 잠가둠(새로 작성할 땐 처음부터 편집 가능).
  const [locked, setLocked] = useState(!!existing);
  const [deleteOpen, setDeleteOpen] = useState(false);

  // 아직 거래 목록을 못 받아왔거나 이 trade_id에 해당하는 거래를 못 찾은 경우.
  if (!rawTrade) {
    return (
      <Screen back contentStyle={styles.loadingContent}>
        <Spinner />
      </Screen>
    );
  }

  const trade = {
    id: rawTrade.id,
    stock: rawTrade.종목명,
    date: formatDate(rawTrade.거래일자),
    type: rawTrade.거래구분 === '매도' ? ('sell' as const) : ('buy' as const),
    amount: rawTrade.거래금액.toLocaleString(),
  };

  const filled = reason.trim().length > 0 && emotion.length > 0 && review.trim().length > 0;
  const isBuy = trade.type === 'buy';

  const handleSave = async () => {
    if (journalId != null) {
      await saveJournal(journalId, { reason, emotion, review });
    } else {
      await createJournalEntry(trade.id, { reason, emotion, review });
    }
    navigation.goBack();
  };

  const handleDelete = async () => {
    if (existing) await deleteJournal(existing.id);
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
            <View style={risk ? undefined : styles.badgeHidden}>
              <StatusBadge risk={risk ?? 'safe'} />
            </View>
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
  loadingContent: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  badgeHidden: { opacity: 0 },
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
    outlineWidth: 0,
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
