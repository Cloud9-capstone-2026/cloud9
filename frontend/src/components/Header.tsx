import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { C, shadow } from '../theme/tokens';
import { Logo } from '../assets/Logo';
import { IconBack, IconUpload, IconBell } from '../assets/icons';
import { goToUpload } from '../navigation/navigationRef';

export function Header({ back }: { back?: boolean }) {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();

  return (
    <View style={[styles.header, { paddingTop: (insets.top || 0) + 12 }]}>
      <View style={styles.left}>
        {back ? (
          <Pressable onPress={() => navigation.goBack()} style={[styles.backBtn, shadow.header]}>
            <IconBack size={20} />
          </Pressable>
        ) : (
          <Logo />
        )}
      </View>
      <View style={styles.right}>
        <Pressable onPress={goToUpload} style={[styles.uploadBtn, shadow.header]}>
          <IconUpload size={13} />
          <Text style={styles.uploadLabel}>업로드</Text>
        </Pressable>
        <View>
          <Pressable style={[styles.bellBtn, shadow.header]}>
            <IconBell size={18} />
          </Pressable>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>3</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: C.bg,
    paddingBottom: 14,
    paddingHorizontal: 22,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  left: { flexDirection: 'row', alignItems: 'center' },
  right: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  backBtn: {
    backgroundColor: C.card,
    padding: 8,
    borderRadius: 20,
  },
  uploadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: C.blue,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 15,
  },
  uploadLabel: { color: '#fff', fontSize: 13, fontWeight: '500' },
  bellBtn: {
    backgroundColor: C.card,
    padding: 9,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: 2,
    right: 2,
    backgroundColor: '#FACC15',
    borderRadius: 999,
    width: 14,
    height: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: { color: '#78350f', fontSize: 9, fontWeight: '700' },
});
