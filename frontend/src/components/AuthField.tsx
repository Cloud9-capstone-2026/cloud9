import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, KeyboardTypeOptions, StyleProp, TextStyle } from 'react-native';
import { C, shadow } from '../theme/tokens';
import { IconEye, IconGoogle, IconNaver } from '../assets/icons';

// Gap between a field's box and the NEXT field's label. Use FIELD_GAP when there's
// no reserved hint/error slot between them, HINT_GAP when there is one (HINT_GAP +
// ErrorText's own footprint === FIELD_GAP), so field rhythm stays constant either way.
export const FIELD_GAP = 28;
export const HINT_GAP = 7;

export function AuthTitle({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.title, style]}>{children}</Text>;
}

export function AuthSubtitle({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.subtitle, style]}>{children}</Text>;
}

// Section label placed above a group of controls (e.g. an email row with a
// separate verify button, or a terms card) — same look as AuthInput's own
// `label` prop, for the cases where there's no single input to attach it to.
export function FieldLabel({ children }: { children: React.ReactNode }) {
  return <Text style={styles.label}>{children}</Text>;
}

export function AuthInput({
  label, value, onChangeText, placeholder, error, editable = true, keyboardType, secureTextEntry, right,
}: {
  label?: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  error?: boolean;
  editable?: boolean;
  keyboardType?: KeyboardTypeOptions;
  secureTextEntry?: boolean;
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
          secureTextEntry={secureTextEntry}
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
      secureTextEntry={!show}
      right={
        <Pressable onPress={onToggleShow} hitSlop={8} style={styles.eyeBtn}>
          <IconEye on={show} size={19} />
        </Pressable>
      }
    />
  );
}

export function ErrorText({ children, color }: { children?: React.ReactNode; color?: string }) {
  return <Text style={[styles.errorText, color ? { color } : null]}>{children || ' '}</Text>;
}

const STRENGTH_META = [
  null,
  { label: '약함', color: '#dc2626' },
  { label: '보통', color: '#FFB800' },
  { label: '안전', color: '#00C807' },
];

export function passwordStrength(pw: string) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[a-zA-Z]/.test(pw) && /[0-9]/.test(pw)) score++;
  if (/[^a-zA-Z0-9]/.test(pw)) score++;
  return score;
}

// Reserved-space hint under a password field: "비밀번호 강도: 약함/보통/안전"
// (label stays muted gray, only the level word is colored).
export function PasswordStrengthHint({ pw }: { pw: string }) {
  const meta = STRENGTH_META[passwordStrength(pw)];
  return (
    <ErrorText color={C.muted}>
      {meta ? <>{'비밀번호 강도: '}<Text style={{ color: meta.color }}>{meta.label}</Text></> : null}
    </ErrorText>
  );
}

export function SocialButton({
  provider, label, onPress,
}: {
  provider: 'google' | 'naver';
  label: string;
  onPress: () => void;
}) {
  const isNaver = provider === 'naver';
  return (
    <Pressable
      style={[styles.socialBtn, isNaver ? styles.naverBtn : [styles.googleBtn, shadow.header]]}
      onPress={onPress}
    >
      <View style={styles.socialIconWrap}>
        {isNaver ? <IconNaver size={30} /> : <IconGoogle size={18} />}
      </View>
      <Text style={[styles.socialText, isNaver && styles.socialTextOnDark]}>{label}</Text>
    </Pressable>
  );
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
  title: { fontSize: 25, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 14, color: '#94a3b8', marginTop: 12 },
  label: { fontSize: 15, fontWeight: '600', color: C.navy, marginBottom: 10, paddingLeft: 2 },
  wrap: { position: 'relative', justifyContent: 'center' },
  input: {
    backgroundColor: '#FFFFFF', borderWidth: 1.5, borderRadius: 16,
    paddingVertical: 14, paddingLeft: 16, fontSize: 16, color: C.navy,
  },
  disabled: { backgroundColor: '#f1f5f9', color: C.muted },
  right: { position: 'absolute', right: 6, padding: 10 },
  eyeBtn: { padding: 0 },
  errorText: { fontSize: 13, color: '#dc2626', lineHeight: 17, minHeight: 17, marginTop: 4},
  cta: { borderRadius: 16, paddingVertical: 17, alignItems: 'center' },
  ctaActive: {
    backgroundColor: C.blue,
    shadowColor: '#16213b', shadowOpacity: 0.10, shadowOffset: { width: 0, height: 2 }, shadowRadius: 10, elevation: 3,
  },
  ctaInactive: { backgroundColor: '#FFFFFF' },
  ctaText: { fontSize: 17, fontWeight: '600' },
  socialBtn: { flexDirection: 'row', alignItems: 'center', height: 52, borderRadius: 16, paddingLeft: 22 },
  googleBtn: { backgroundColor: '#fff' },
  naverBtn: { backgroundColor: '#03C75A' },
  socialIconWrap: { width: 20, alignItems: 'center', overflow: 'visible' },
  socialText: { flex: 1, textAlign: 'center', marginRight: 20, fontSize: 16, fontWeight: '500', color: C.navy },
  socialTextOnDark: { color: '#fff' },
});
