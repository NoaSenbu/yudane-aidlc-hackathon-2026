/**
 * KaiinshoScreen: 会員証画面（v2 デザイン）。
 * useHomeSnapshot + deriveMemberRank 接続（R5）。
 */

import React from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { ApiClient } from '../../features/platform/api-client/api-client';
import { useHomeSnapshot } from '../../features/auth/home/use-home-snapshot';
import {
  deriveMemberRank,
  MEMBER_RANK_DISPLAY,
  MEMBER_RANK_ORDER,
  nextRankInfo,
  rankStageIndex,
} from '../../features/auth/home/member-rank';

interface KaiinshoScreenProps {
  client: ApiClient;
}

const PRIVILEGES = [
  { title: '専属コンシェルジュ 24時間', desc: '黒岩が、夜通し論破します' },
  { title: '深夜の優先お取り置き',       desc: '1:00–6:00 も最優先でご案内' },
  { title: '迷い、全部論破',             desc: '感想は、すべて論破します' },
  { title: '配送料無料 · 最速便',        desc: '翌日14時までにお届け' },
  { title: '専属バトラー帯同 · 限定外商', desc: '縞瑪瑙 ONYX より解禁', locked: true },
];

export function KaiinshoScreen({ client }: KaiinshoScreenProps): React.JSX.Element {
  const { data, isLoading, isError, refetch } = useHomeSnapshot(client);

  const yudaneLevel = data?.yudaneLevel ?? 0;
  const currentRank = deriveMemberRank(yudaneLevel);
  const currentDisplay = MEMBER_RANK_DISPLAY[currentRank];
  const next = nextRankInfo(yudaneLevel);
  const currentStage = rankStageIndex(currentRank);

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-prive-bg">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        {/* 会員証カード */}
        <View className="mx-4 mt-4 rounded-3xl overflow-hidden border border-prive-gold/40 bg-prive-surface">
          {/* カードヘッダー */}
          <View className="px-6 pt-6 pb-4 bg-prive-card">
            <Text className="text-prive-gold text-xs tracking-widest">YUDANE PRIVÉ</Text>
            {isLoading && !data ? (
              <ActivityIndicator color="#C9A96E" style={{ marginTop: 8 }} />
            ) : (
              <Text className="text-prive-gold text-3xl font-bold mt-1 tracking-widest">
                {currentDisplay.en}
              </Text>
            )}
          </View>

          {/* 会員情報 */}
          <View className="px-6 py-5 border-t border-prive-gold/20">
            <Text className="text-prive-cream text-xl font-semibold">悠介 様</Text>
            <View className="flex-row gap-6 mt-3">
              <View>
                <Text className="text-prive-muted text-xs">MEMBER SINCE</Text>
                <Text className="text-prive-cream font-semibold mt-0.5">2024</Text>
              </View>
              <View>
                <Text className="text-prive-muted text-xs">委ね Lv</Text>
                <Text className="text-prive-cream font-semibold mt-0.5">
                  {data ? String(yudaneLevel) : '…'}
                </Text>
              </View>
            </View>
          </View>
        </View>

        {/* ランク進行 */}
        <View className="mx-4 mt-4 bg-prive-surface border border-prive-border rounded-2xl p-5">
          <Text className="text-prive-muted text-xs tracking-widest mb-4">STANDING</Text>
          {isError ? (
            <View>
              <Text style={{ color: '#E05A5A', fontSize: 13 }}>ランクを取得できませんでした</Text>
              <Pressable onPress={() => refetch()} className="mt-2">
                <Text className="text-prive-gold text-xs">再取得</Text>
              </Pressable>
            </View>
          ) : (
            <>
              <View className="flex-row justify-between">
                {MEMBER_RANK_ORDER.map((rank, idx) => {
                  const isActive = rank === currentRank;
                  const isPast = idx < currentStage;
                  const rankDisp = MEMBER_RANK_DISPLAY[rank];
                  return (
                    <View key={rank} className="items-center flex-1">
                      {/* コネクター */}
                      {idx > 0 && (
                        <View
                          className={`absolute left-0 top-2.5 right-1/2 h-px ${
                            isPast || isActive ? 'bg-prive-gold/50' : 'bg-prive-border'
                          }`}
                        />
                      )}
                      {/* ドット */}
                      <View
                        className={`w-5 h-5 rounded-full border-2 ${
                          isActive
                            ? 'bg-prive-gold border-prive-gold'
                            : isPast
                              ? 'bg-prive-gold/40 border-prive-gold/40'
                              : 'bg-prive-bg border-prive-border'
                        }`}
                      />
                      <Text
                        className={`text-xs mt-1 text-center ${
                          isActive ? 'text-prive-gold font-bold' : 'text-prive-muted'
                        }`}
                      >
                        {rankDisp.en}
                      </Text>
                      <Text
                        className={`text-xs text-center ${
                          isActive ? 'text-prive-cream' : 'text-prive-muted'
                        }`}
                      >
                        {rankDisp.ja}
                      </Text>
                    </View>
                  );
                })}
              </View>

              {next && (
                <View className="mt-4 bg-prive-card rounded-xl px-4 py-3">
                  <Text className="text-prive-muted text-xs">
                    {MEMBER_RANK_DISPLAY[next.nextRank].ja}{' '}{MEMBER_RANK_DISPLAY[next.nextRank].en} まで、あと
                    <Text className="text-prive-gold font-bold"> {next.remaining}回 </Text>
                    のご用命。
                  </Text>
                </View>
              )}
            </>
          )}
        </View>

        {/* PRIVILEGES */}
        <View className="mx-4 mt-4 mb-6 bg-prive-surface border border-prive-border rounded-2xl p-5">
          <Text className="text-prive-muted text-xs tracking-widest mb-4">
            {currentDisplay.en} PRIVILEGES
          </Text>
          {PRIVILEGES.map((priv) => (
            <View
              key={priv.title}
              className={`flex-row items-start gap-3 mb-4 ${priv.locked ? 'opacity-40' : ''}`}
            >
              <View className="w-1.5 h-1.5 rounded-full bg-prive-gold mt-1.5" />
              <View className="flex-1">
                <Text className="text-prive-cream text-sm font-semibold">{priv.title}</Text>
                <Text className="text-prive-muted text-xs mt-0.5">{priv.desc}</Text>
              </View>
              {priv.locked && <Text className="text-prive-muted text-xs">🔒</Text>}
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
