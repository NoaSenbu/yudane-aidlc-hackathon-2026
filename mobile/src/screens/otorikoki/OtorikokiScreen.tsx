/**
 * OtorikokiScreen: お取り置き（カート介入）画面（v2 デザイン）。
 * useCartWatchItems + useCartDismiss + filterWatchItems + useAmazonRedirect 接続（R3, R4, R6）。
 */

import React, { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { ReelApiClient } from '../../features/reel/reel-api';
import { useAmazonRedirect } from '../../features/reel/use-amazon-redirect';
import { useCartWatchItems } from '../../features/cart/use-cart-watch-items';
import { useCartDismiss } from '../../features/cart/use-cart-dismiss';
import {
  filterWatchItems,
  aggregateWatchItems,
  STATUS_LABEL,
  type FilterTab,
} from '../../features/cart/watch-item-filter';
import type { CartWatchItemDto } from '../../features/cart/use-cart-watch-item';

interface OtorikokiScreenProps {
  reelClient: ReelApiClient;
}

const C = {
  gold: '#C9A96E',
  teal: '#4DCFC0',
  cream: '#E8E0D0',
  muted: '#6A6A8A',
  bg: '#080814',
  surface: '#10101E',
  border: '#28285A',
  rouge: '#E05A5A',
};

const FILTER_TABS: FilterTab[] = ['すべて', 'おすすめ', 'まもなく', '休眠'];

function statusColor(status: CartWatchItemDto['status']): string {
  if (status === 'watching') return C.gold;
  if (status === 'notified-30m' || status === 'notified-6h' || status === 'notified-24h') return C.teal;
  if (status === 'watching_orphaned' || status === 'purchased' || status === 'dismissed') return C.muted;
  return C.cream;
}

function cardBorderColor(status: CartWatchItemDto['status']): string {
  if (status === 'watching') return 'rgba(201,169,110,0.4)';
  if (status === 'notified-30m' || status === 'notified-6h' || status === 'notified-24h') return 'rgba(77,207,192,0.4)';
  return C.border;
}

export function OtorikokiScreen({ reelClient }: OtorikokiScreenProps): React.JSX.Element {
  const [filterTab, setFilterTab] = useState<FilterTab>('すべて');

  const { data, isLoading, isError, refetch } = useCartWatchItems({ limit: 20 });
  const dismiss = useCartDismiss();
  const { redirect, isPending: isRedirecting } = useAmazonRedirect(reelClient);

  const allItems = data?.items ?? [];
  const filtered = filterWatchItems(allItems, filterTab);
  const { count, totalYen } = aggregateWatchItems(filtered);

  // ─── ローディング ──────────────────────────────────────────────────────────
  if (isLoading && !data) {
    return (
      <SafeAreaView edges={['top']} style={[s.root, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator color={C.gold} size="large" />
        <Text style={[s.metaText, { marginTop: 12 }]}>お取り置きを確認中…</Text>
      </SafeAreaView>
    );
  }

  // ─── エラー ────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <SafeAreaView edges={['top']} style={[s.root, { justifyContent: 'center', alignItems: 'center', paddingHorizontal: 32 }]}>
        <Text style={[s.productName, { textAlign: 'center' }]}>
          お取り置きリストを取得できませんでした
        </Text>
        <Pressable onPress={() => refetch()} style={{ marginTop: 16, backgroundColor: C.gold, borderRadius: 12, paddingHorizontal: 24, paddingVertical: 12 }}>
          <Text style={{ color: C.bg, fontWeight: 'bold' }}>再取得</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top']} style={s.root}>
      {/* ヘッダー */}
      <View style={s.header}>
        <Text style={s.headerLabel}>ON HOLD FOR YOU</Text>
        <View style={s.headerRow}>
          <Text style={s.headerCount}>{count}点</Text>
          <Text style={s.headerTotal}> · ¥{(totalYen / 10000).toFixed(1)}万</Text>
        </View>
        <View style={s.headerRow}>
          <Text style={s.headerMuted}>次の論破まで</Text>
          <Text style={s.headerCountdown}>まもなく</Text>
          <Text style={s.headerMuted}>なんですよね。</Text>
        </View>
      </View>

      {/* フィルタータブ */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={s.filterScroll}
        contentContainerStyle={s.filterContent}
      >
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

      {/* 空状態 */}
      {filtered.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <Text style={s.metaText}>このカテゴリのアイテムはありません</Text>
        </View>
      ) : (
        <ScrollView style={s.list} contentContainerStyle={s.listContent} showsVerticalScrollIndicator={false}>
          {filtered.map((item) => (
            <View key={item.itemId} style={[s.card, { borderColor: cardBorderColor(item.status) }]}>
              {/* 商品情報行 */}
              <View style={s.cardTop}>
                <View style={s.cardInfo}>
                  <View style={s.statusRow}>
                    <Text style={[s.statusBadge, { color: statusColor(item.status) }]}>
                      {STATUS_LABEL[item.status]}
                    </Text>
                  </View>
                  <Text style={s.productName}>{item.productMeta.title}</Text>
                </View>
                <Text style={s.priceText}>¥{item.productMeta.priceYen.toLocaleString()}</Text>
              </View>

              {/* アクション行 */}
              <View style={s.actionRow}>
                {/* 論破して買う */}
                <Pressable
                  style={[s.debateButton, { flex: 1 }]}
                  disabled={isRedirecting}
                  onPress={() =>
                    void redirect({
                      cardId: item.itemId,
                      asin: item.asin,
                      context: 'cart-attack',
                    })
                  }
                >
                  <Text style={s.debateButtonText}>
                    {isRedirecting ? '遷移中…' : '論破して買う'}
                  </Text>
                </Pressable>

                {/* 解除 */}
                <Pressable
                  style={s.dismissButton}
                  disabled={dismiss.isPending}
                  onPress={() => dismiss.mutate(item.asin)}
                >
                  <Text style={s.dismissButtonText}>解除</Text>
                </Pressable>
              </View>
            </View>
          ))}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:               { flex: 1, backgroundColor: C.bg },
  header:             { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 12 },
  headerLabel:        { color: C.muted, fontSize: 11, letterSpacing: 2 },
  headerRow:          { flexDirection: 'row', alignItems: 'baseline', marginTop: 4 },
  headerCount:        { color: C.cream, fontSize: 20, fontWeight: 'bold' },
  headerTotal:        { color: C.muted, fontSize: 14 },
  headerMuted:        { color: C.muted, fontSize: 12 },
  headerCountdown:    { color: C.gold, fontSize: 14, fontWeight: 'bold', marginHorizontal: 4 },
  filterScroll:       { flexGrow: 0, marginBottom: 12 },
  filterContent:      { paddingHorizontal: 16, gap: 8, flexDirection: 'row' },
  filterChip:         { paddingHorizontal: 16, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: C.border },
  filterChipActive:   { backgroundColor: C.gold, borderColor: C.gold },
  filterChipText:     { color: C.muted, fontSize: 12 },
  filterChipTextActive: { color: C.bg, fontWeight: 'bold' },
  list:               { flex: 1, paddingHorizontal: 16 },
  listContent:        { paddingBottom: 24 },
  card:               { backgroundColor: C.surface, borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 12 },
  cardTop:            { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardInfo:           { flex: 1 },
  statusRow:          { flexDirection: 'row', alignItems: 'center', marginBottom: 4, gap: 8 },
  statusBadge:        { fontSize: 12, fontWeight: '600' },
  metaText:           { color: C.muted, fontSize: 12 },
  productName:        { color: C.cream, fontWeight: '600', fontSize: 15 },
  priceText:          { color: C.cream, fontWeight: 'bold', fontSize: 15, marginLeft: 8 },
  actionRow:          { flexDirection: 'row', gap: 8, marginTop: 12 },
  debateButton:       { borderWidth: 1, borderColor: 'rgba(201,169,110,0.5)', borderRadius: 12, paddingVertical: 10, alignItems: 'center' },
  debateButtonText:   { color: C.gold, fontSize: 14 },
  dismissButton:      { borderWidth: 1, borderColor: C.border, borderRadius: 12, paddingVertical: 10, paddingHorizontal: 16, alignItems: 'center' },
  dismissButtonText:  { color: C.muted, fontSize: 14 },
});
