/**
 * MainTabs: YUDANE PRIVÉ 底部タブナビゲーター（v2 デザイン）。
 *
 * 5タブ: ホーム / お見立て / お取り置き / ご相談 / 会員証
 * React Navigation は使わず、Pressable + View でシンプルに実装。
 */

import React, { useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { ApiClient } from '../features/platform/api-client/api-client';
import type { ReelApiClient } from '../features/reel/reel-api';
import { GosodanScreen } from '../screens/gosodan/GosodanScreen';
import { HomeScreen } from '../screens/home/HomeScreen';
import { KaiinshoScreen } from '../screens/kaiinsho/KaiinshoScreen';
import { MitateScreen } from '../screens/mitate/MitateScreen';
import { OtorikokiScreen } from '../screens/otorikoki/OtorikokiScreen';

export type TabId = 'home' | 'mitate' | 'otorikoki' | 'gosodan' | 'kaiinsho';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'home',      label: 'ホーム',     icon: '⌂' },
  { id: 'mitate',    label: 'お見立て',   icon: '◈' },
  { id: 'otorikoki', label: 'お取り置き', icon: '◻' },
  { id: 'gosodan',   label: 'ご相談',     icon: '◇' },
  { id: 'kaiinsho',  label: '会員証',     icon: '◉' },
];

interface MainTabsProps {
  client: ApiClient;
}

export function MainTabs({ client }: MainTabsProps): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>('home');

  /** ApiClient → ReelApiClient アダプタ（MitateScreen / OtorikokiScreen 用）。 */
  const reelClient: ReelApiClient = useMemo(
    () => ({
      apiFetch: function apiFetch<T>(path: string, init?: { method?: string; body?: unknown }) {
        return client.request<T>(path, {
          method: init?.method,
          body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
        });
      },
    }),
    [client],
  );

  function renderScreen(): React.JSX.Element {
    switch (activeTab) {
      case 'home':
        return <HomeScreen onNavigate={setActiveTab} client={client} />;
      case 'mitate':
        return <MitateScreen client={client} reelClient={reelClient} onNavigate={setActiveTab} />;
      case 'otorikoki':
        return <OtorikokiScreen reelClient={reelClient} />;
      case 'gosodan':
        return <GosodanScreen />;
      case 'kaiinsho':
        return <KaiinshoScreen client={client} />;
    }
  }

  return (
    <View className="flex-1 bg-prive-bg">
      {/* 画面コンテンツ */}
      <View className="flex-1">{renderScreen()}</View>

      {/* 底部タブバー */}
      <SafeAreaView edges={['bottom']} className="bg-prive-surface border-t border-prive-border">
        <View className="flex-row">
          {TABS.map((tab) => {
            const isActive = tab.id === activeTab;
            return (
              <Pressable
                key={tab.id}
                testID={`tab-${tab.id}`}
                accessibilityRole="tab"
                accessibilityState={{ selected: isActive }}
                className="flex-1 items-center py-3"
                onPress={() => setActiveTab(tab.id)}
              >
                <Text
                  className={isActive ? 'text-prive-gold text-base' : 'text-prive-muted text-base'}
                >
                  {tab.icon}
                </Text>
                <Text
                  className={`text-xs mt-0.5 ${isActive ? 'text-prive-gold' : 'text-prive-muted'}`}
                >
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </SafeAreaView>
    </View>
  );
}
