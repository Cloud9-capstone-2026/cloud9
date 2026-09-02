import React from 'react';
import { View, Text, Pressable, TextInput, StyleSheet } from 'react-native';
import { C } from '../theme/tokens';
import { RULES, MONEY_LABEL } from '../data/mock';
import { useAppState } from '../state/AppState';

function fmtMoney(n: number) {
  return n > 0 ? n.toLocaleString() : '';
}

export function ruleInvalid(id: string, ruleOn: Record<string, boolean>, ruleVal: Record<string, number>, ruleMoney: Record<string, number>) {
  const r = RULES.find((x) => x.id === id)!;
  if (!ruleOn[id]) return false;
  if (r.isMoney) return !(ruleMoney[id] >= 1);
  if (r.unit === null) return false;
  return !(ruleVal[id] >= 1);
}

export function rulesAllValid(ruleOn: Record<string, boolean>, ruleVal: Record<string, number>, ruleMoney: Record<string, number>) {
  return RULES.every((r) => !ruleInvalid(r.id, ruleOn, ruleVal, ruleMoney));
}

export function RuleCardList({ showBanner }: { showBanner?: boolean }) {
  const { ruleOn, ruleVal, ruleMoney, toggleRule, setRuleVal, setRuleMoney } = useAppState();

  return (
    <View style={{ gap: 10 }}>
      {showBanner && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>규칙을 바꿔도 이미 나온 리포트는 그대로예요. 다음 업로드부터 적용됩니다.</Text>
        </View>
      )}
      {RULES.map((r) => {
        const on = ruleOn[r.id];
        const showInput = on && (r.isMoney || r.unit !== null);
        const invalid = ruleInvalid(r.id, ruleOn, ruleVal, ruleMoney);
        return (
          <View key={r.id} style={styles.card}>
            <View style={styles.headRow}>
              <View style={{ flex: 1, minWidth: 0, paddingRight: 12 }}>
                <Text style={styles.name}>{r.name}</Text>
                <Text style={styles.desc}>{r.desc}</Text>
              </View>
              <Pressable
                onPress={() => toggleRule(r.id)}
                style={[styles.switchTrack, { backgroundColor: on ? C.blue : C.border }]}
              >
                <View style={[styles.switchKnob, { left: on ? 21 : 3 }]} />
              </Pressable>
            </View>
            {showInput && (
              <View style={styles.inputArea}>
                <View style={styles.inputRow}>
                  <Text style={styles.inputLabel}>{r.isMoney ? MONEY_LABEL : r.label}</Text>
                  <View style={styles.inputBox}>
                    <TextInput
                      value={r.isMoney ? fmtMoney(ruleMoney[r.id] || 0) : String(ruleVal[r.id] ?? '')}
                      onChangeText={(t) => {
                        const raw = t.replace(/[^0-9]/g, '');
                        const n = raw === '' ? 0 : Number(raw);
                        if (r.isMoney) setRuleMoney(r.id, n);
                        else setRuleVal(r.id, n);
                      }}
                      keyboardType="number-pad"
                      style={styles.input}
                    />
                  </View>
                  {!r.isMoney && <Text style={styles.unit}>{r.unit}</Text>}
                  {r.isMoney && <Text style={styles.unit}>원</Text>}
                </View>
                <Text style={styles.errorText}>{invalid ? '값을 입력해주세요' : ''}</Text>
              </View>
            )}
          </View>
        );
      })}
      <Text style={styles.footerNote}>켜둔 규칙에 해당하는 거래는 리포트에서 규칙 기반 계층에 표시됩니다.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { backgroundColor: '#e8f0ff', borderRadius: 14, paddingVertical: 11, paddingHorizontal: 13 },
  bannerText: { fontSize: 13, color: C.blue, lineHeight: 18 },
  card: { backgroundColor: '#fff', borderRadius: 22, paddingVertical: 15, paddingHorizontal: 16 },
  headRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  name: { fontSize: 16, fontWeight: '600', color: C.navy, marginBottom: 3 },
  desc: { fontSize: 13, color: C.muted, lineHeight: 18 },
  switchTrack: { width: 44, height: 26, borderRadius: 999, justifyContent: 'center', flexShrink: 0 },
  switchKnob: {
    position: 'absolute', width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff',
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 2,
  },
  inputArea: { marginTop: 13, paddingTop: 13, borderTopWidth: 1, borderTopColor: C.border },
  inputRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 10 },
  inputLabel: { fontSize: 15, color: C.navy, flex: 1 },
  inputBox: { width: 140, backgroundColor: '#f1f5f9', borderRadius: 12, paddingVertical: 10, paddingHorizontal: 12 },
  input: { fontSize: 17, fontWeight: '600', color: C.navy, textAlign: 'right', padding: 0 },
  unit: { fontSize: 15, fontWeight: '600', color: C.navy },
  errorText: { fontSize: 11, color: '#dc2626', textAlign: 'right', marginTop: 4, minHeight: 13 },
  footerNote: { fontSize: 12, color: '#cbd5e1', paddingHorizontal: 4 },
});
