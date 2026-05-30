/**
 * HomeScreen: YUDANE PRIVÉ ホーム画面（v2 モックアップ移植）。
 */

import React from 'react';
import { ScrollView, Text, View, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { TabId } from '../../navigation/MainTabs';

export interface HomeScreenProps {
  onNavigate: (tab: TabId) => void;
}

export function HomeScreen({ onNavigate }: HomeScreenProps): React.JSX.Element {
  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        {/* ヘッダー */}
        <View className="px-6 pt-4 pb-2 flex-row justify-between items-start">
          <View>
            <Text className="text-prive-muted text-xs tracking-widest">YUDANE PRIVÉ</Text>
            <Text className="text-prive-muted text-xs">MEMBER · NOIR</Text>
          </View>
          <Text className="text-prive-muted text-xs">金曜日 · 23:47</Text>
        </View>

        {/* ウェルカムカード */}
        <View className="mx-4 mt-2 rounded-2xl bg-prive-surface border border-prive-border p-5">
          <Text className="text-prive-cream text-lg font-semibold">悠介さん、おかえりなさい。</Text>
          <Text className="text-prive-muted text-sm mt-1">
            今日も会議{' '}
            <Text className="text-prive-gold font-bold">6本</Text>
            {'\n'}ご褒美なしって、勝てます？
          </Text>
          <Pressable
            className="mt-4 bg-prive-gold rounded-xl py-3 items-center"
            onPress={() => onNavigate('mitate')}
          >
            <Text className="text-prive-bg font-bold text-sm tracking-wider">
              お見立てを見る
            </Text>
          </Pressable>
        </View>

        {/* YOUR STANDING */}
        <View className="mx-4 mt-4 rounded-2xl bg-prive-surface border border-prive-border p-5">
          <Text className="text-prive-muted text-xs tracking-widest mb-3">YOUR STANDING</Text>
          <View className="flex-row items-baseline gap-2">
            <Text className="text-prive-gold text-2xl font-bold">漆黒</Text>
            <Text className="text-prive-cream text-lg">NOIR</Text>
          </View>
          <Text className="text-prive-muted text-sm mt-1">
            本年のお任せ{' '}
            <Text className="text-prive-cream font-bold">24</Text>
            {' '}回
          </Text>
          <View className="mt-3 bg-prive-card rounded-xl p-3">
            <Text className="text-prive-muted text-xs">
              次のランク{' '}
              <Text className="text-prive-cream">縞瑪瑙 ONYX</Text>
              {'\n'}まであと
              <Text className="text-prive-gold font-bold"> 1回 </Text>
              なんですよね。ここで止まる理由、あります？
            </Text>
          </View>
        </View>

        {/* 統計行 */}
        <View className="mx-4 mt-4 flex-row gap-3">
          {[
            { label: 'お取り置き', value: '14', unit: '点' },
            { label: '今月のご用命', value: '¥58.2', unit: '万' },
            { label: '代行成約', value: '78', unit: '%' },
          ].map((stat) => (
            <View key={stat.label} className="flex-1 bg-prive-surface border border-prive-border rounded-2xl p-4 items-center">
              <Text className="text-prive-muted text-xs text-center">{stat.label}</Text>
              <View className="flex-row items-baseline mt-1">
                <Text className="text-prive-cream font-bold text-lg">{stat.value}</Text>
                <Text className="text-prive-muted text-xs ml-0.5">{stat.unit}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* 今日の論破 */}
        <View className="mx-4 mt-4 mb-6">
          <View className="flex-row justify-between items-center mb-3">
            <Text className="text-prive-cream text-sm font-semibold">
              今日、論破しときました
            </Text>
            <Text className="text-prive-gold text-xs">4 ITEMS</Text>
          </View>

          {/* 優先アイテム */}
          <Pressable
            className="bg-prive-surface border border-prive-gold/30 rounded-2xl p-4 mb-3"
            onPress={() => onNavigate('otorikoki')}
          >
            <View className="flex-row justify-between items-start">
              <View className="flex-1">
                <Text className="text-prive-gold text-xs tracking-wider">おすすめ</Text>
                <Text className="text-prive-cream font-semibold mt-1">Sony WF-1000XM6</Text>
                <Text className="text-prive-muted text-xs mt-0.5">36時間お取り置き中</Text>
              </View>
              <Text className="text-prive-cream font-bold">¥24,800</Text>
            </View>
          </Pressable>

          {/* 最近の対応 */}
          <Text className="text-prive-muted text-xs tracking-widest mb-2">RECENTLY ATTENDED</Text>
          {[
            { name: 'Anker USB-C ハブ', ago: '3日前', status: '論破済み', price: '¥6,480', statusColor: 'text-prive-teal' },
            { name: 'COMOLI バンドカラーシャツ', ago: '5日前', status: '逃げた', price: '¥24,200', statusColor: 'text-prive-rouge' },
          ].map((item) => (
            <View
              key={item.name}
              className="bg-prive-surface border border-prive-border rounded-xl p-3 mb-2 flex-row justify-between items-center"
            >
              <View className="flex-1">
                <Text className="text-prive-cream text-sm">{item.name}</Text>
                <View className="flex-row items-center gap-2 mt-0.5">
                  <Text className="text-prive-muted text-xs">{item.ago}</Text>
                  <Text className={`text-xs ${item.statusColor}`}>{item.status}</Text>
                </View>
              </View>
              <Text className="text-prive-muted text-sm">{item.price}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
