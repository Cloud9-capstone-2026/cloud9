import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, KeyboardTypeOptions } from 'react-native';
import { C } from '../theme/tokens';
import { IconEye } from '../assets/icons';

export function AuthInput({
  label, value, onChangeText, placeholder, error, editable = true, keyboardType, right,
}: {
  label?: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  error?: boolean;
  editable?: boolean;
  keyboardType?: KeyboardTypeOptions;
  right?: React.ReactNode;
}) {
  const [focused, setFocused] = useState(false);
  const borderColor = error ? '#dc2626' : focused ? C.blue : 'transparent';
  return (
    <View>
      {label && <Text style={styles.label}>{label}</Text>}
      <View style={styles.wrap}>
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={C.muted}
          editable={editable}
          keyboardType={keyboardType}
          autoCapitalize="none"
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={[
            styles.input,
            { borderColor, paddingRight: right ? 44 : 16 },
            !editable && styles.disabled,
          ]}
        />
        {right && <View style={styles.right}>{right}</View>}
      </View>
    </View>
  );
}

export function PasswordInput({
  label, value, onChangeText, placeholder, error, show, onToggleShow,
}: {
  label?: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  error?: boolean;
  show: boolean;
  onToggleShow: () => void;
}) {
  return (
    <AuthInput
      label={label}
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      error={error}
      keyboardType={undefined}
      right={
        <Pressable onPress={onToggleShow} hitSlop={8} style={styles.eyeBtn}>
          <IconEye on={show} size={19} />
        </Pressable>
      }
    />
  );
}

export function ErrorText({ children }: { children?: string | null }) {
  return <Text style={styles.errorText}>{children || ' '}</Text>;
}

export function CtaButton({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <Pressable
      onPress={active ? onPress : undefined}
      style={[styles.cta, active ? styles.ctaActive : styles.ctaInactive]}
    >
      <Text style={[styles.ctaText, { color: active ? '#fff' : '#94a3b8' }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 15, fontWeight: '600', color: C.navy, marginBottom: 10, paddingLeft: 2 },
  wrap: { position: 'relative', justifyContent: 'center' },
  input: {
    backgroundColor: '#FFFFFF', borderWidth: 1.5, borderRadius: 16,
    paddingVertical: 14, paddingLeft: 16, fontSize: 16, color: C.navy,
  },
  disabled: { backgroundColor: '#f1f5f9', color: C.muted },
  right: { position: 'absolute', right: 6, padding: 10 },
  eyeBtn: { padding: 0 },
  errorText: { fontSize: 13, color: '#dc2626', lineHeight: 17, minHeight: 17 },
  cta: { borderRadius: 16, paddingVertical: 16, alignItems: 'center' },
  ctaActive: {
    backgroundColor: C.blue,
    shadowColor: '#16213b', shadowOpacity: 0.10, shadowOffset: { width: 0, height: 2 }, shadowRadius: 10, elevation: 3,
  },
  ctaInactive: { backgroundColor: '#FFFFFF' },
  ctaText: { fontSize: 17, fontWeight: '600' },
});
