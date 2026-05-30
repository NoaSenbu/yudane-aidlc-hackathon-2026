/**
 * MitateScreen: お見立て（リール）画面（v2 デザイン）。
 *
 * 「黒岩の論破リスト」形式で商品を縦スワイプ。
 * 既存 ReelScreen ロジック（gestures / hooks）を流用し、
 * v2 PRIVÉ スタイルで上書きする。
 */

import React, { useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

interface MitateCard {
  lot: number;
  total: number;
  name: string;
  brand: string;
  category: string;
  priceYen: number;
  pitch: string;
  subPoints: string[];
  nextItems: { name: string; reason: string; priceYen: number }[];
}

const MOCK_CARD: MitateCard = {
  lot: 2,
  total: 8,
  name: 'WF-1000XM6',
  brand: 'SONY · オーディオ',
  category: 'SONY · オーディオ',
  priceYen: 24800,
  pitch: '会議6本の夜に。時給換算で 11時間分 なんですよ。これ買わない理由、なんかあります？',
  subPoints: ['会議6本の夜', '同僚の8割が所有'],
  nextItems: [
    { name: 'COMOLI シャツ', reason: '土曜のデートに', priceYen: 24200 },
    { name: 'Santal 33', reason: '初対面ではないが', priceYen: 24500 },
    { name: 'Brain Sleep', reason: '深夜の労いに', priceYen: 7200 },
  ],
};

export function MitateScreen(): React.JSX.Element {
  const [currentLot, setCurrentLot] = useState(MOCK_CARD.lot);

  function handleRefuse(): void {
    Alert.alert(
      '感想で見送る',
      '「今日は見送ります」\n\n黒岩: それ感想ですよね。また明日、データで話しましょう。',
      [{ text: '閉じる' }],
    );
  }

  function handleBuy(): void {
    Alert.alert(
      '論破されて買う',
      `Sony WF-1000XM6\n¥${MOCK_CARD.priceYen.toLocaleString()}\n\nAmazon に遷移します。\n（Unit-3 Debate 論破完了画面は今後実装予定）`,
      [
        { text: 'やめとく', style: 'cancel' },
        { text: 'Amazon で買う', onPress: () => setCurrentLot((n) => n + 1) },
      ],
    );
  }

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        {/* ヘッダー */}
        <View className="px-6 pt-4 pb-3 flex-row justify-between items-center">
          <View>
            <Text className="text-prive-muted text-xs tracking-widest">黒岩の論破リスト</Text>
            <Text className="text-prive-cream text-sm font-semibold">本日 8点</Text>
          </View>
          <Text className="text-prive-gold text-xs">
            LOT {String(currentLot).padStart(2, '0')} / {String(MOCK_CARD.total).padStart(2, '0')}
          </Text>
        </View>

        {/* メインカード */}
        <View className="mx-4 rounded-2xl bg-prive-surface border border-prive-border overflow-hidden">
          {/* 商品カテゴリ */}
          <View className="px-5 pt-5 pb-3 border-b border-prive-border">
            <Text className="text-prive-muted text-xs tracking-widest">{MOCK_CARD.category}</Text>
            <Text className="text-prive-cream text-2xl font-bold mt-1">{MOCK_CARD.name}</Text>
            <Text className="text-prive-gold font-bold text-xl mt-0.5">
              ¥{MOCK_CARD.priceYen.toLocaleString()}
            </Text>
          </View>

          {/* 論破ピッチ */}
          <View className="px-5 py-4">
            <Text className="text-prive-cream text-base leading-relaxed">{MOCK_CARD.pitch}</Text>

            {/* サブポイント */}
            <View className="mt-4 gap-2">
              {MOCK_CARD.subPoints.map((point) => (
                <View key={point} className="flex-row items-center gap-2">
                  <View className="w-1 h-1 rounded-full bg-prive-gold" />
                  <Text className="text-prive-muted text-sm">{point}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* アクション */}
          <View className="px-4 pb-5 gap-3">
            <Pressable
              testID="mitate-buy"
              className="bg-prive-gold rounded-xl py-4 items-center"
              onPress={handleBuy}
            >
              <Text className="text-prive-bg font-bold tracking-wider">
                論破されて買う · ¥{MOCK_CARD.priceYen.toLocaleString()}
              </Text>
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
            <Text className="text-prive-gold text-xs">全8点を見る</Text>
          </View>
          {MOCK_CARD.nextItems.map((item) => (
            <View
              key={item.name}
              className="flex-row justify-between items-center bg-prive-surface border border-prive-border rounded-xl px-4 py-3 mb-2"
            >
              <View>
                <Text className="text-prive-cream text-sm">{item.name}</Text>
                <Text className="text-prive-muted text-xs">{item.reason}</Text>
              </View>
              <Text className="text-prive-muted text-sm">¥{item.priceYen.toLocaleString()}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
