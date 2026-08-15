import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { useNavigation } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { IconCloud, IconFile } from '../assets/icons';
import { C } from '../theme/tokens';
import { uploadHistoryRaw } from '../data/mock';

interface PickedFile {
  name: string;
  meta: string;
}

const REQUIRED_COLUMNS = ['거래일자', '종목명', '거래구분', '거래수량', '거래단가'];

export function UploadScreen() {
  const navigation = useNavigation();
  const [file, setFile] = useState<PickedFile | null>(null);

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
    setFile({ name: asset.name, meta: `${kb ? `${kb.toLocaleString()} KB · ` : ''}${ext}` });
  };

  const handleAction = () => {
    if (!file) {
      pickFile();
    } else {
      setFile(null);
      navigation.goBack();
    }
  };

  return (
    <Screen back contentStyle={styles.content}>
      <Text style={styles.title}>파일 업로드</Text>

      <View style={[styles.dropzone, file ? styles.dropzoneFilled : styles.dropzoneEmpty]}>
        {!file ? (
          <View style={styles.emptyInner}>
            <IconCloud size={38} />
            <View style={{ alignItems: 'center' }}>
              <Text style={styles.dzText}>파일을 드래그하거나 선택하세요</Text>
              <Text style={styles.dzSub}>CSV, XLSX 형식 지원</Text>
            </View>
          </View>
        ) : (
          <View style={styles.fileChip}>
            <View style={styles.fileIconBox}>
              <IconFile size={18} />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
              <Text style={styles.fileMeta}>{file.meta}</Text>
            </View>
            <Pressable onPress={() => setFile(null)} hitSlop={8}>
              <Text style={styles.removeBtn}>×</Text>
            </Pressable>
          </View>
        )}
        <Pressable onPress={handleAction} style={styles.actionBtn}>
          <Text style={styles.actionBtnText}>{file ? '업로드 하기' : '파일 선택'}</Text>
        </Pressable>
      </View>

      <Card>
        <Text style={styles.cardTitle}>필수 컬럼</Text>
        <View style={styles.chipsRow}>
          {REQUIRED_COLUMNS.map((c) => (
            <View key={c} style={styles.columnChip}>
              <Text style={styles.columnChipText}>{c}</Text>
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <Text style={styles.cardTitle}>업로드 히스토리</Text>
        {uploadHistoryRaw.map((u, i) => (
          <View key={u.id} style={[styles.historyRow, i > 0 && styles.historyDivider]}>
            <View>
              <Text style={styles.historyFilename}>{u.filename}</Text>
              <Text style={styles.historyMeta}>{u.date} · {u.count}건</Text>
            </View>
            <View style={styles.doneBadge}>
              <Text style={styles.doneBadgeText}>완료</Text>
            </View>
          </View>
        ))}
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 18 },
  title: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  dropzone: {
    borderRadius: 30, paddingVertical: 38, paddingHorizontal: 20, minHeight: 232,
    alignItems: 'center', justifyContent: 'center', gap: 16,
  },
  dropzoneEmpty: { borderWidth: 2, borderStyle: 'dashed', borderColor: C.border, backgroundColor: C.card },
  dropzoneFilled: { backgroundColor: C.card },
  emptyInner: { alignItems: 'center', gap: 14 },
  dzText: { fontSize: 14, fontWeight: '500', color: C.navy, lineHeight: 21 },
  dzSub: { fontSize: 12, color: C.muted, marginTop: 4 },
  fileChip: {
    width: '100%', flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: C.mutedBg, borderRadius: 20, paddingVertical: 14, paddingHorizontal: 16,
  },
  fileIconBox: {
    width: 38, height: 38, borderRadius: 12, backgroundColor: '#e8f0ff',
    alignItems: 'center', justifyContent: 'center',
  },
  fileName: { fontSize: 13, fontWeight: '500', color: C.navy, lineHeight: 19 },
  fileMeta: { fontSize: 11, color: C.muted, marginTop: 2 },
  removeBtn: { color: C.muted, fontSize: 18, lineHeight: 18, padding: 4 },
  actionBtn: { backgroundColor: C.blue, borderRadius: 999, paddingVertical: 10, paddingHorizontal: 26 },
  actionBtnText: { color: '#fff', fontSize: 13, fontWeight: '500' },
  cardTitle: { fontSize: 13, fontWeight: '500', color: C.navy, marginBottom: 12 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
  columnChip: { backgroundColor: '#e8f0ff', borderRadius: 999, paddingVertical: 5, paddingHorizontal: 12 },
  columnChipText: { color: C.blue, fontSize: 12, fontWeight: '500' },
  historyRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12 },
  historyDivider: { borderTopWidth: 1, borderTopColor: C.border },
  historyFilename: { fontSize: 13, fontWeight: '500', color: C.navy, lineHeight: 19 },
  historyMeta: { fontSize: 11, color: C.muted, marginTop: 2 },
  doneBadge: { backgroundColor: '#00C807', borderRadius: 999, paddingVertical: 3, paddingHorizontal: 10 },
  doneBadgeText: { color: '#fff', fontSize: 11, fontWeight: '500' },
});
