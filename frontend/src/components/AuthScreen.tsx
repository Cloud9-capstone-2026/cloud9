import React from 'react';
import { View, ScrollView, Pressable, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { C, shadow } from '../theme/tokens';
import { IconBack } from '../assets/icons';

export function AuthScreen({
  back, onBack, headerRight, children,
}: {
  back?: boolean;
  onBack?: () => void;
  // Extra controls (e.g. upload/notification buttons) shown next to the back
  // button — used when this layout is reused for main-app sub-screens.
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}) {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();

  return (
    <View style={styles.root}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.content, { paddingTop: (insets.top || 0) + 12 }]}
        keyboardShouldPersistTaps="handled"
      >
        {(back || headerRight) && (
          <View style={styles.headerRow}>
            {back ? (
              <Pressable
                onPress={onBack || (() => navigation.goBack())}
                style={[styles.backBtn, shadow.header]}
              >
                <IconBack size={20} />
              </Pressable>
            ) : <View />}
            {headerRight}
          </View>
        )}
        {children}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  content: { paddingHorizontal: 22, paddingBottom: 32, flexGrow: 1 },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 },
  backBtn: { backgroundColor: C.card, alignSelf: 'flex-start', padding: 8, borderRadius: 20 },
});
