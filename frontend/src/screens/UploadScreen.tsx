import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { ConfirmModal } from '../components/ConfirmModal';
import { IconCloud, IconFile } from '../assets/icons';
import { C, text } from '../theme/tokens';
import { uploadHistoryRaw } from '../data/mock';
import { useAppState } from '../state/AppState';
import { goToUploadHistory } from '../navigation/navigationRef';
import type { RootStackParamList } from '../navigation/types';

const ALLOWED_EXT = ['csv', 'xlsx', 'xls'];
const MAX_BYTES = 10 * 1024 * 1024;

interface PickedFile {
  name: string;
  meta: string;
  sizeKB: number | null;
  ext: string;
}

function validate(name: string, sizeBytes: number | null): string | null {
  const ext = (name.split('.').pop() || '').toLowerCase();
  if (!ALLOWED_EXT.includes(ext)) return 'CSV, XLSX, XLS 형식만 업로드할 수 있어요.';
  if (sizeBytes === 0) return '내용이 없는 파일이에요. 다른 파일을 선택해 주세요.';
  if (sizeBytes !== null && sizeBytes > MAX_BYTES) return '파일 용량이 10MB를 초과했어요.';
  return null;
}

export function UploadScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { setUpFile, hasUploaded } = useAppState();
  const [file, setFile] = useState<PickedFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dupOpen, setDupOpen] = useState(false);

  const pickFile = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: [
        'text/csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
      ],
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets?.length) return;
    const asset = result.assets[0];
    const ext = (asset.name.split('.').pop() || '').toUpperCase();
    const kb = asset.size ? Math.max(1, Math.round(asset.size / 1024)) : null;
    setFile({ name: asset.name, meta: `${kb ? `${kb.toLocaleString()} KB · ` : ''}${ext}`, sizeKB: kb, ext });
    setError(validate(asset.name, asset.size ?? null));
  };

  const startUpload = () => {
    if (!file) return;
    setUpFile({ name: file.name, sizeKB: file.sizeKB, ext: file.ext });
    navigation.navigate('Uploading');
  };

  const handleAction = () => {
    if (!file) {
      pickFile();
      return;
    }
    if (error) return;
    const isDup = uploadHistoryRaw.some((u) => u.filename === file.name);
    if (isDup) {
      setDupOpen(true);
      return;
    }
    startUpload();
  };

  const recent = hasUploaded ? uploadHistoryRaw.slice(0, 5) : [];

  return (
    <Screen back contentStyle={styles.content}>
      <View>
        <Text style={text.screenTitle}>파일 업로드</Text>
        <Text style={[text.screenSubtitle, styles.subtitle]}>{'증권사에서 내려받은 거래내역 파일을 올려\n분석을 시작해보세요.'}</Text>
      </View>

      <View style={[styles.dropzone, file ? styles.dropzoneFilled : styles.dropzoneEmpty]}>
        <View style={styles.dzTop}>
          {!file ? (
            <View style={styles.emptyInner}>
              <IconCloud size={38} />
              <View style={{ alignItems: 'center' }}>
                <Text style={styles.dzText}>파일을 드래그하거나 선택하세요</Text>
                <Text style={styles.dzSub}>CSV, XLSX, XLS · 최대 10MB</Text>
              </View>
            </View>
          ) : (
            <View style={{ width: '100%' }}>
              <View style={styles.fileChip}>
                <View style={styles.fileIconBox}>
                  <IconFile size={18} />
                </View>
                <View style={{ flex: 1, minWidth: 0 }}>
                  <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                  <Text style={styles.fileMeta}>{file.meta}</Text>
                </View>
                <Pressable onPress={() => { setFile(null); setError(null); }} hitSlop={8}>
                  <Text style={styles.removeBtn}>×</Text>
                </Pressable>
              </View>
              {error && <Text style={styles.fileError}>{error}</Text>}
            </View>
          )}
        </View>
        <Pressable
          onPress={handleAction}
          disabled={!!(file && error)}
          style={[styles.actionBtn, file && error ? styles.actionBtnDisabled : null]}
        >
          <Text style={[styles.actionBtnText, file && error ? styles.actionBtnTextDisabled : null]}>
            {file ? '업로드 하기' : '파일 선택'}
          </Text>
        </Pressable>
      </View>

      <View>
        <View style={styles.historyHeader}>
          <Text style={styles.cardTitle}>최근 업로드 히스토리</Text>
          <Pressable onPress={goToUploadHistory}>
            <Text style={styles.more}>더보기 &gt;</Text>
          </Pressable>
        </View>
        <Card style={styles.historyCard}>
          {recent.length === 0 ? (
            <View style={styles.historyEmpty}>
              <Text style={styles.emptyText}>아직 업로드한 파일이 없어요</Text>
            </View>
          ) : (
            recent.map((u, i) => (
              <View key={u.id} style={[styles.historyRow, i > 0 && styles.historyDivider]}>
                <View style={{ flex: 1, minWidth: 0, paddingRight: 10 }}>
                  <Text style={styles.historyFilename} numberOfLines={1}>{u.filename}</Text>
                  <Text style={styles.historyMeta}>{u.date}</Text>
                </View>
                <Text style={styles.historyCount}>{u.count}건</Text>
              </View>
            ))
          )}
        </Card>
      </View>

      <ConfirmModal
        visible={dupOpen}
        title="이미 올린 파일이에요"
        body={'업로드 히스토리에 동일한 이름의 파일이 존재해요.\n계속할까요?'}
        confirmLabel="계속하기"
        confirmColor={C.blue}
        onConfirm={() => { setDupOpen(false); startUpload(); }}
        onCancel={() => setDupOpen(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 24 },
  subtitle: { marginTop: 3 },
  dropzone: {
    borderRadius: 30, paddingVertical: 24, paddingHorizontal: 20, minHeight: 232,
    justifyContent: 'space-between',
  },
  dropzoneEmpty: { borderWidth: 2, borderStyle: 'dashed', borderColor: C.border, backgroundColor: C.card },
  dropzoneFilled: { borderWidth: 2, borderColor: 'transparent', backgroundColor: C.card },
  dzTop: { flex: 1, justifyContent: 'center' },
  emptyInner: { alignItems: 'center', gap: 14 },
  dzText: { fontSize: 16, fontWeight: '500', color: C.navy, lineHeight: 21 },
  dzSub: { fontSize: 13, color: C.muted, marginTop: 4 },
  fileChip: {
    width: '100%', flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: C.mutedBg, borderRadius: 20, paddingVertical: 14, paddingHorizontal: 16,
  },
  fileIconBox: {
    width: 38, height: 38, borderRadius: 12, backgroundColor: '#e8f0ff',
    alignItems: 'center', justifyContent: 'center',
  },
  fileName: { fontSize: 15, fontWeight: '500', color: C.navy, lineHeight: 19 },
  fileMeta: { fontSize: 12, color: C.muted, marginTop: 2 },
  removeBtn: { color: C.muted, fontSize: 20, lineHeight: 18, padding: 4 },
  fileError: { fontSize: 13, color: '#dc2626', marginTop: 10 },
  actionBtn: { width: '100%', backgroundColor: C.blue, borderRadius: 30, paddingVertical: 14, alignItems: 'center' },
  actionBtnDisabled: { backgroundColor: '#e2e8f0' },
  actionBtnText: { color: '#fff', fontSize: 16, fontWeight: '500' },
  actionBtnTextDisabled: { color: '#94a3b8' },
  historyHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, paddingHorizontal: 2 },
  cardTitle: { fontSize: 15, fontWeight: '500', color: C.navy },
  more: { fontSize: 13, color: C.muted },
  historyCard: { minHeight: 302, justifyContent: 'center' },
  historyEmpty: { alignItems: 'center', justifyContent: 'center', minHeight: 270 },
  emptyText: { fontSize: 15, color: '#64748b' },
  historyRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12 },
  historyDivider: { borderTopWidth: 1, borderTopColor: C.border },
  historyFilename: { fontSize: 15, fontWeight: '500', color: C.navy, lineHeight: 19 },
  historyMeta: { fontSize: 12, color: C.muted, marginTop: 2 },
  historyCount: { fontSize: 16, fontWeight: '600', color: C.navy, flexShrink: 0 },
});
