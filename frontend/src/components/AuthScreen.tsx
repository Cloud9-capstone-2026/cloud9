import React from 'react';
import { View, ScrollView, Pressable, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { C, shadow } from '../theme/tokens';
import { IconBack } from '../assets/icons';

export function AuthScreen({
  back, onBack, children,
}: {
  back?: boolean;
  onBack?: () => void;
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
        {back && (
          <Pressable
            onPress={onBack || (() => navigation.goBack())}
            style={[styles.backBtn, shadow.header]}
          >
            <IconBack size={20} />
          </Pressable>
        )}
        {children}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  content: { paddingHorizontal: 22, paddingBottom: 32, flexGrow: 1 },
  backBtn: { backgroundColor: C.card, alignSelf: 'flex-start', padding: 8, borderRadius: 20, marginBottom: 18 },
});
