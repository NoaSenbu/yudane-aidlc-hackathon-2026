/**
 * OtorikokiScreen: お取り置き（カート介入）画面（v2 デザイン）。
 */

import React, { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

type ItemStatus = 'おすすめ' | '新着' | '保留' | '休眠';

interface HoldItem {
  id: string;
  name: string;
  priceYen: number;
  status: ItemStatus;
  timeLabel: string;
  nextActionLabel: string;
  viewCount: number;
}

const MOCK_ITEMS: HoldItem[] = [
  { id: 'sony', name: 'Sony WF-1000XM6', priceYen: 24800, status: 'おすすめ', timeLabel: '36時間前', nextActionLabel: '24時間後にご案内', viewCount: 3 },
  { id: 'anker', name: 'Anker USB-C Hub 8-in-1', priceYen: 6480, status: '新着', timeLabel: '2時間前', nextActionLabel: '30分後にご案内', viewCount: 1 },
  { id: 'lelabo', name: 'Le Labo Santal 33', priceYen: 24500, status: '保留', timeLabel: '8時間前', nextActionLabel: '6時間後にご案内', viewCount: 5 },
  { id: 'hhkb', name: 'HHKB Professional HYBRID', priceYen: 32800, status: '休眠', timeLabel: '5日前', nextActionLabel: '休眠中', viewCount: 12 },
  { id: 'brainsleep', name: '@aroma Brain Sleep', priceYen: 7200, status: '保留', timeLabel: '12時間前', nextActionLabel: '12時間後にご案内', viewCount: 2 },
];

const C = {
  gold: '#C9A96E',
  teal: '#4DCFC0',
  cream: '#E8E0D0',
  muted: '#6A6A8A',
  bg: '#080814',
  surface: '#10101E',
  border: '#28285A',
};

function statusColor(status: ItemStatus): string {
  if (status === 'おすすめ') return C.gold;
  if (status === '新着') return C.teal;
  if (status === '保留') return C.cream;
  return C.muted;
}

function cardBorderColor(status: ItemStatus): string {
  if (status === 'おすすめ') return 'rgba(201,169,110,0.4)';
  if (status === '新着') return 'rgba(77,207,192,0.4)';
  return C.border;
}

const FILTER_TABS = ['すべて', 'おすすめ', 'まもなく', '休眠'] as const;
type FilterTab = (typeof FILTER_TABS)[number];

export function OtorikokiScreen(): React.JSX.Element {
  const [filterTab, setFilterTab] = useState<FilterTab>('すべて');
  const total = MOCK_ITEMS.reduce((sum, i) => sum + i.priceYen, 0);

  return (
    <SafeAreaView edges={['top']} style={s.root}>
      {/* ヘッダー */}
      <View style={s.header}>
        <Text style={s.headerLabel}>ON HOLD FOR YOU</Text>
        <View style={s.headerRow}>
          <Text style={s.headerCount}>{MOCK_ITEMS.length}点</Text>
          <Text style={s.headerTotal}> · ¥{(total / 10000).toFixed(1)}万</Text>
        </View>
        <View style={s.headerRow}>
          <Text style={s.headerMuted}>次の論破まで</Text>
          <Text style={s.headerCountdown}>23分</Text>
          <Text style={s.headerMuted}>なんですよね。</Text>
        </View>
      </View>

      {/* フィルタータブ */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.filterScroll} contentContainerStyle={s.filterContent}>
        {FILTER_TABS.map((tab) => {
          const active = filterTab === tab;
          return (
            <Pressable
              key={tab}
              style={[s.filterChip, active && s.filterChipActive]}
              onPress={() => setFilterTab(tab)}
            >
              <Text style={[s.filterChipText, active && s.filterChipTextActive]}>{tab}</Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {/* アイテム一覧 */}
      <ScrollView style={s.list} contentContainerStyle={s.listContent} showsVerticalScrollIndicator={false}>
        {MOCK_ITEMS.map((item) => (
          <View key={item.id} style={[s.card, { borderColor: cardBorderColor(item.status) }]}>
            {/* 商品情報行 */}
            <View style={s.cardTop}>
              <View style={s.cardInfo}>
                <View style={s.statusRow}>
                  <Text style={[s.statusBadge, { color: statusColor(item.status) }]}>{item.status}</Text>
                  <Text style={s.metaText}>{item.timeLabel}</Text>
                  <Text style={s.metaText}>{item.viewCount}度ご覧</Text>
                </View>
                <Text style={s.productName}>{item.name}</Text>
                <Text style={s.nextAction}>{item.nextActionLabel}</Text>
              </View>
              <Text style={s.priceText}>¥{item.priceYen.toLocaleString()}</Text>
            </View>

            {/* 論破ボタン */}
            <Pressable
              style={s.debateButton}
              onPress={() => {
                Alert.alert(
                  '論破して買う',
                  `「${item.name}」\n\n黒岩が今すぐ論破します。`,
                  [{ text: '閉じる' }],
                );
              }}
            >
              <Text style={s.debateButtonText}>論破して買う</Text>
            </Pressable>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 12 },
  headerLabel: { color: C.muted, fontSize: 11, letterSpacing: 2 },
  headerRow: { flexDirection: 'row', alignItems: 'baseline', marginTop: 4 },
  headerCount: { color: C.cream, fontSize: 20, fontWeight: 'bold' },
  headerTotal: { color: C.muted, fontSize: 14 },
  headerMuted: { color: C.muted, fontSize: 12 },
  headerCountdown: { color: C.gold, fontSize: 14, fontWeight: 'bold', marginHorizontal: 4 },
  filterScroll: { flexGrow: 0, marginBottom: 12 },
  filterContent: { paddingHorizontal: 16, gap: 8, flexDirection: 'row' },
  filterChip: { paddingHorizontal: 16, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: C.border },
  filterChipActive: { backgroundColor: C.gold, borderColor: C.gold },
  filterChipText: { color: C.muted, fontSize: 12 },
  filterChipTextActive: { color: C.bg, fontWeight: 'bold' },
  list: { flex: 1, paddingHorizontal: 16 },
  listContent: { paddingBottom: 24 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 12 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardInfo: { flex: 1 },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4, gap: 8 },
  statusBadge: { fontSize: 12, fontWeight: '600' },
  metaText: { color: C.muted, fontSize: 12 },
  productName: { color: C.cream, fontWeight: '600', fontSize: 15 },
  nextAction: { color: C.muted, fontSize: 12, marginTop: 2 },
  priceText: { color: C.cream, fontWeight: 'bold', fontSize: 15, marginLeft: 8 },
  debateButton: { marginTop: 12, borderWidth: 1, borderColor: 'rgba(201,169,110,0.5)', borderRadius: 12, paddingVertical: 10, alignItems: 'center' },
  debateButtonText: { color: C.gold, fontSize: 14 },
});
