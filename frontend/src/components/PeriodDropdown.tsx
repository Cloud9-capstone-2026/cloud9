import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { C, shadow, PERIODS } from '../theme/tokens';

export function PeriodDropdown({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);

  return (
    <View style={styles.wrap}>
      <Pressable onPress={() => setOpen((v) => !v)} style={[styles.btn, shadow.header]}>
        <Text style={styles.btnLabel}>{value}</Text>
        <View style={styles.caret}>
          <Text style={styles.caretChar}>▲</Text>
          <Text style={styles.caretChar}>▼</Text>
        </View>
      </Pressable>
      {open && (
        <View style={[styles.dropdown, shadow.dropdown]}>
          {PERIODS.map((p) => {
            const active = p === value;
            return (
              <Pressable
                key={p}
                onPress={() => { onChange(p); setOpen(false); }}
                style={[styles.opt, active && styles.optActive]}
              >
                <Text style={{ fontSize: 13, color: active ? C.blue : '#64748b', fontWeight: active ? '600' : '400' }}>
                  {p.replace('최근 ', '')}
                </Text>
              </Pressable>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'relative', zIndex: 30 },
  btn: {
    width: 92, backgroundColor: '#FFFFFF', borderRadius: 10, paddingVertical: 5, paddingHorizontal: 11,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  btnLabel: { fontSize: 13, color: '#64748b' },
  caret: { alignItems: 'center', gap: 2 },
  caretChar: { fontSize: 7, color: '#94a3b8', lineHeight: 6 },
  dropdown: {
    position: 'absolute', top: 32, right: 0, width: 92, backgroundColor: '#FFFFFF',
    borderRadius: 12, padding: 5, zIndex: 30,
  },
  opt: { borderRadius: 8, paddingVertical: 7, paddingHorizontal: 8 },
  optActive: { backgroundColor: '#e8f0ff' },
});
