import React from 'react';
import { View, Text, Image, Pressable, StyleSheet } from 'react-native';
import { getCharacter } from '../constants/characterAssets';
import { C } from '../theme/tokens';

export function InvestorTypeBadge({
  typeCode,
  size = 100,
  onStartDiagnosis,
}: {
  // null/undefined = 자가진단을 한 번도 안 한 상태(빈 상태 표시) — 3번 요구사항.
  typeCode?: string | null;
  size?: number;
  onStartDiagnosis?: () => void;
}) {
  if (!typeCode) {
    return (
      <View style={styles.wrap}>
        <View style={{ width: size, height: size }} />
        <Text style={styles.emptyText}>아직 자가진단을 하지 않았어요</Text>
        {onStartDiagnosis && (
          <Pressable onPress={onStartDiagnosis}>
            <Text style={styles.emptyCta}>검사 시작하기 →</Text>
          </Pressable>
        )}
      </View>
    );
  }

  const character = getCharacter(typeCode);
  return (
    <View style={styles.wrap}>
      {character.image ? (
        <Image source={character.image} style={{ width: size, height: size }} />
      ) : (
        <View style={{ width: size, height: size }} />
      )}
      <Text style={styles.name}>{character.name}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 8 },
  name: { fontSize: 16, fontWeight: '600', color: C.navy },
  emptyText: { fontSize: 13, color: C.muted },
  emptyCta: { fontSize: 13, fontWeight: '600', color: C.blue },
});
