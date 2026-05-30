/**
 * MitateScreen: お見立て（リール）画面（v2 デザイン）。
 * useReelFeed + useAmazonRedirect 接続（R2, R6, R7）。
 */

import React, { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { ApiClient } from '../../features/platform/api-client/api-client';
import type { ReelApiClient } from '../../features/reel/reel-api';
import { useReelFeed } from '../../features/reel/use-reel-feed';
import { useAmazonRedirect } from '../../features/reel/use-amazon-redirect';
import type { ReelCard } from '../../features/reel/types';
import type { TabId } from '../../navigation/MainTabs';

interface MitateScreenProps {
  client: ApiClient;
  reelClient: ReelApiClient;
  onNavigate: (tab: TabId) => void;
}

export function MitateScreen({ reelClient, onNavigate }: MitateScreenProps): React.JSX.Element {
  const feed = useReelFeed(reelClient);
  const { redirect, isPending: isRedirecting } = useAmazonRedirect(reelClient);
  const [currentIndex, setCurrentIndex] = useState(0);

  const allCards: ReelCard[] = useMemo(
    () => feed.data?.pages.flatMap((p) => p.cards) ?? [],
    [feed.data],
  );

  const currentCard = allCards[currentIndex] ?? null;
  const upNext = allCards.slice(currentIndex + 1);
  const totalCards = allCards.length;

  function handleRefuse(): void {
    setCurrentIndex((i) => i + 1);
  }

  function handleBuy(): void {
    if (!currentCard) return;
    void redirect({
      cardId: currentCard.cardId,
      asin: currentCard.product.asin,
      context: 'reel',
    });
  }

  // ─── ローディング ────────────────────────────────────────────────────────────
  if (feed.isLoading) {
    return (
      <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg items-center justify-center">
        <ActivityIndicator color="#C9A96E" size="large" />
        <Text className="text-prive-muted text-sm mt-3">黒岩が選定中…</Text>
      </SafeAreaView>
    );
  }

  // ─── エラー ───────────────────────────────────────────────────────────────────
  if (feed.isError) {
    return (
      <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg items-center justify-center px-8">
        <Text className="text-prive-cream text-base font-semibold text-center">
          お見立てを取得できませんでした
        </Text>
        <Pressable
          className="mt-4 bg-prive-gold rounded-xl px-6 py-3"
          onPress={() => feed.refetch()}
        >
          <Text className="text-prive-bg font-bold">再取得</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  // ─── 空状態（全カード見送り済み or 0件）──────────────────────────────────────
  if (!currentCard) {
    return (
      <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg items-center justify-center px-8">
        <Text className="text-prive-gold text-lg font-bold text-center">本日の論破リスト 完了</Text>
        <Text className="text-prive-muted text-sm text-center mt-2">
          黒岩が明日また用意します。
        </Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        {/* ヘッダー */}
        <View className="px-6 pt-4 pb-3 flex-row justify-between items-center">
          <View>
            <Text className="text-prive-muted text-xs tracking-widest">黒岩の論破リスト</Text>
            <Text className="text-prive-cream text-sm font-semibold">本日 {totalCards}点</Text>
          </View>
          <Text className="text-prive-gold text-xs">
            LOT {String(currentIndex + 1).padStart(2, '0')} / {String(totalCards).padStart(2, '0')}
          </Text>
        </View>

        {/* メインカード */}
        <View className="mx-4 rounded-2xl bg-prive-surface border border-prive-border overflow-hidden">
          {/* 商品情報 */}
          <View className="px-5 pt-5 pb-3 border-b border-prive-border">
            <Text className="text-prive-muted text-xs tracking-widest">
              {currentCard.origin.replace(/-/g, ' ').toUpperCase()}
            </Text>
            <Text className="text-prive-cream text-2xl font-bold mt-1">
              {currentCard.product.title}
            </Text>
            <Text className="text-prive-gold font-bold text-xl mt-0.5">
              ¥{currentCard.product.priceYen.toLocaleString()}
            </Text>
          </View>

          {/* 論破ピッチ */}
          <View className="px-5 py-4">
            <Text className="text-prive-cream text-base leading-relaxed">
              {currentCard.pitch}
            </Text>

            {/* 所有感ラベル */}
            <View className="mt-4 bg-prive-card rounded-xl px-4 py-3">
              <Text className="text-prive-gold text-xs font-semibold">
                {currentCard.ownershipLabel.text}
              </Text>
              <Text className="text-prive-muted text-xs mt-0.5">
                {currentCard.ownershipLabel.rationale}
              </Text>
            </View>

            {/* タグ */}
            {currentCard.tags.length > 0 && (
              <View className="mt-3 flex-row gap-2 flex-wrap">
                {currentCard.tags.map((tag) => (
                  <View key={tag} className="bg-prive-surface border border-prive-border rounded-full px-3 py-1">
                    <Text className="text-prive-muted text-xs">{tag}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>

          {/* アクション */}
          <View className="px-4 pb-5 gap-3">
            <Pressable
              testID="mitate-gosodan"
              className="bg-prive-gold rounded-xl py-4 items-center"
              onPress={() => onNavigate('gosodan')}
            >
              <Text className="text-prive-bg font-bold tracking-wider">相談する</Text>
            </Pressable>
            <Pressable
              testID="mitate-refuse"
              className="border border-prive-border rounded-xl py-3 items-center"
              onPress={handleRefuse}
            >
              <Text className="text-prive-muted">感想で見送る</Text>
            </Pressable>
          </View>
        </View>

        {/* UP NEXT */}
        <View className="mx-4 mt-4 mb-6">
          <View className="flex-row justify-between items-center mb-3">
            <Text className="text-prive-muted text-xs tracking-widest">UP NEXT · 次のお見立て</Text>
            <Text className="text-prive-gold text-xs">全{totalCards}点</Text>
          </View>
          {upNext.length === 0 ? (
            <Text className="text-prive-muted text-xs">次のアイテムはありません</Text>
          ) : (
            upNext.map((item) => (
              <View
                key={item.cardId}
                className="flex-row justify-between items-center bg-prive-surface border border-prive-border rounded-xl px-4 py-3 mb-2"
              >
                <View className="flex-1">
                  <Text className="text-prive-cream text-sm">{item.product.title}</Text>
                  <Text className="text-prive-muted text-xs">{item.ownershipLabel.text}</Text>
                </View>
                <Text className="text-prive-muted text-sm">
                  ¥{item.product.priceYen.toLocaleString()}
                </Text>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
