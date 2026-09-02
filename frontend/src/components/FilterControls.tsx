import React from 'react';
import { View, Text, Pressable, StyleSheet, TextInput } from 'react-native';
import { C, shadow } from '../theme/tokens';
import { IconSearch } from '../assets/icons';

export type TypeFilter = 'all' | 'buy' | 'sell';
export type RiskFilter = 'all' | 'danger' | 'caution' | 'safe';

const TYPE_LABEL: Record<TypeFilter, string> = { all: '전체', buy: '매수', sell: '매도' };
const RISK_LABEL: Record<RiskFilter, string> = { all: '전체', danger: '이상', caution: '경고', safe: '정상' };

export function TypeTabs({ value, onChange }: { value: TypeFilter; onChange: (v: TypeFilter) => void }) {
  const options: TypeFilter[] = ['all', 'buy', 'sell'];
  return (
    <View style={styles.tabRow}>
      {options.map((t) => {
        const active = value === t;
        return (
          <Pressable key={t} onPress={() => onChange(t)} style={[styles.tab, active && styles.tabActive]}>
            <Text style={[styles.tabLabel, { color: active ? C.navy : C.muted, fontWeight: active ? '600' : '400' }]}>
              {TYPE_LABEL[t]}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function SortToggle({ newest, onToggle }: { newest: boolean; onToggle: () => void }) {
  return (
    <View style={styles.sortRow}>
      <Text style={styles.sortLabel}>{newest ? '최신순' : '오래된순'}</Text>
      <Pressable onPress={onToggle} style={[styles.switchTrack, { backgroundColor: newest ? C.blue : C.border }]}>
        <View style={[styles.switchKnob, { left: newest ? 19 : 2.5 }]} />
      </Pressable>
    </View>
  );
}

export function SearchInput({
  value, onChangeText, placeholder,
}: { value: string; onChangeText: (v: string) => void; placeholder: string }) {
  return (
    <View style={styles.searchWrap}>
      <View style={styles.searchIcon}>
        <IconSearch size={16} />
      </View>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={C.muted}
        style={styles.searchInput}
      />
    </View>
  );
}

export function RiskChips({ value, onChange }: { value: RiskFilter; onChange: (v: RiskFilter) => void }) {
  const options: RiskFilter[] = ['all', 'danger', 'caution', 'safe'];
  return (
    <View style={styles.chipRow}>
      {options.map((r) => {
        const active = value === r;
        return (
          <Pressable
            key={r}
            onPress={() => onChange(r)}
            style={[styles.chip, { backgroundColor: active ? C.blue : C.card }]}
          >
            <Text style={{ fontSize: 13, color: active ? '#fff' : C.muted, fontWeight: active ? '500' : '400' }}>
              {RISK_LABEL[r]}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Pagination({
  page, totalPages, onChange,
}: { page: number; totalPages: number; onChange: (page: number) => void }) {
  if (totalPages <= 1) return null;
  const pages = Array.from({ length: totalPages }, (_, i) => i);
  return (
    <View style={styles.pagerRow}>
      <Pressable
        onPress={() => onChange(Math.max(0, page - 1))}
        disabled={page === 0}
        style={[styles.pagerBtn, shadow.header]}
      >
        <Text style={{ fontSize: 17, color: page === 0 ? C.muted : C.navy }}>‹</Text>
      </Pressable>
      {pages.map((p) => (
        <Pressable
          key={p}
          onPress={() => onChange(p)}
          style={[styles.pagerNumBtn, shadow.header, { backgroundColor: p === page ? C.blue : C.card }]}
        >
          <Text style={{ fontSize: 15, color: p === page ? '#fff' : C.navy, fontWeight: p === page ? '500' : '400' }}>
            {p + 1}
          </Text>
        </Pressable>
      ))}
      <Pressable
        onPress={() => onChange(Math.min(totalPages - 1, page + 1))}
        disabled={page === totalPages - 1}
        style={[styles.pagerBtn, shadow.header]}
      >
        <Text style={{ fontSize: 17, color: page === totalPages - 1 ? C.muted : C.navy }}>›</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  tabRow: { flexDirection: 'row', gap: 20 },
  tab: { paddingVertical: 5, paddingTop: 2, borderBottomWidth: 2, borderBottomColor: 'transparent' },
  tabActive: { borderBottomColor: C.navy },
  tabLabel: { fontSize: 16, lineHeight: 21 },
  sortRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sortLabel: { fontSize: 13, color: C.muted },
  switchTrack: { width: 40, height: 23, borderRadius: 999, justifyContent: 'center' },
  switchKnob: {
    position: 'absolute', width: 18, height: 18, borderRadius: 9, backgroundColor: '#fff',
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 2,
  },
  searchWrap: { position: 'relative', marginBottom: 12, justifyContent: 'center' },
  searchIcon: { position: 'absolute', left: 12, zIndex: 1 },
  searchInput: {
    width: '100%', paddingVertical: 10, paddingRight: 12, paddingLeft: 32,
    borderBottomWidth: 1.5, borderBottomColor: '#555', fontSize: 15, color: C.navy,
  },
  chipRow: { flexDirection: 'row', gap: 7, marginBottom: 16, flexWrap: 'wrap' },
  chip: { borderRadius: 999, paddingVertical: 10, paddingHorizontal: 14 },
  pagerRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 6, marginTop: 16 },
  pagerBtn: { backgroundColor: C.card, borderRadius: 20, paddingVertical: 7, paddingHorizontal: 13 },
  pagerNumBtn: { borderRadius: 20, paddingVertical: 7, paddingHorizontal: 12, minWidth: 36, alignItems: 'center' },
});
