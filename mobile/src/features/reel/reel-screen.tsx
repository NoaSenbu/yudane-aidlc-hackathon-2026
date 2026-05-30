/**
 * M-03 ReelScreen: 縦型スワイプリール画面（UC-02）。
 *
 * TDD 例外（AGENTS.md §12.3）: mockup/index.html の reel 画面の機械的移植。
 * ロジック（ジェスチャー判定 / 遷移記録 / フィード取得 / 誘導アニメ）は別ファイルの
 * 純関数・フックでテスト済み（gestures / boost-nudge / reel-api / use-*）。
 * 本ファイルは仮想化リスト + GestureLayer + 確認オーバーレイの結線（R-PAT-UI-01）。
 */

import { useCallback, useRef, useState } from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';

import { resolveGesture, type GestureAction } from './gestures';
import type { ReelApiClient } from './reel-api';
import type { ReelCard } from './types';
import { useAmazonRedirect } from './use-amazon-redirect';
import { useReelFeed } from './use-reel-feed';

/** ReelScreen の props。 */
export interface ReelScreenProps {
  client: ReelApiClient;
  /** 左スワイプで論破画面へ遷移（Unit-3）。 */
  onNavigateDebate: (card: ReelCard, trigger: 'reel-refuse') => void;
  /** 右スワイプでカート監視登録（Unit-5）。 */
  onRegisterCartWatch: (card: ReelCard) => void;
  /** Amazon 遷移後のレポート自動遷移。 */
  onTransitionComplete: () => void;
  /** 「論破不要」設定。 */
  debateDisabled?: boolean;
}

/**
 * 縦型リール画面。
 *
 * @param props - 画面 props。
 * @returns リール画面要素。
 */
export function ReelScreen(props: ReelScreenProps): React.JSX.Element {
  const { client, onNavigateDebate, onRegisterCartWatch, onTransitionComplete, debateDisabled } =
    props;
  const feed = useReelFeed(client);
  const redirect = useAmazonRedirect(client);
  const [overlayCard, setOverlayCard] = useState<ReelCard | null>(null);
  const leftSwipeCounts = useRef<Record<string, number>>({});

  const cards: ReelCard[] = (feed.data?.pages ?? []).flatMap((page) => page.cards);

  const dispatch = useCallback(
    (action: GestureAction, card: ReelCard): void => {
      switch (action) {
        case 'navigate-debate':
          onNavigateDebate(card, 'reel-refuse');
          break;
        case 'register-cart-watch':
          onRegisterCartWatch(card);
          break;
        case 'show-transition-overlay':
          setOverlayCard(card);
          break;
        // skip-toast / cooldown-blocked / next-card は UI トースト or 無処理
        default:
          break;
      }
    },
    [onNavigateDebate, onRegisterCartWatch],
  );

  const onSwipeLeft = useCallback(
    (card: ReelCard): void => {
      const count = (leftSwipeCounts.current[card.cardId] ?? 0) + 1;
      leftSwipeCounts.current[card.cardId] = count;
      dispatch(
        resolveGesture({ gesture: 'swipe-left', dx: -80, debateDisabled, leftSwipeCount: count }),
        card,
      );
    },
    [dispatch, debateDisabled],
  );

  const confirmTransition = useCallback(
    (card: ReelCard): void => {
      redirect.mutate(card, {
        onSuccess: () => {
          setOverlayCard(null);
          onTransitionComplete();
        },
      });
    },
    [redirect, onTransitionComplete],
  );

  return (
    <View testID="reel-screen" className="flex-1 bg-indigo-950">
      <FlatList
        testID="reel-feed-list"
        data={cards}
        keyExtractor={(card) => card.cardId}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        onEndReached={() => {
          if (feed.hasNextPage) void feed.fetchNextPage();
        }}
        renderItem={({ item }) => (
          <ReelCardView
            card={item}
            onSwipeLeft={() => onSwipeLeft(item)}
            onSwipeRight={() =>
              dispatch(resolveGesture({ gesture: 'swipe-right', dx: 80 }), item)
            }
            onDoubleTap={() =>
              dispatch(resolveGesture({ gesture: 'double-tap', tapIntervalMs: 200 }), item)
            }
          />
        )}
      />
      {overlayCard !== null ? (
        <AmazonTransitionOverlay
          card={overlayCard}
          onConfirm={() => confirmTransition(overlayCard)}
          onCancel={() => setOverlayCard(null)}
        />
      ) : null}
    </View>
  );
}

/** リールカード 1 枚（mockup .reel-card の移植）。 */
function ReelCardView(props: {
  card: ReelCard;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  onDoubleTap: () => void;
}): React.JSX.Element {
  const { card, onSwipeLeft, onSwipeRight, onDoubleTap } = props;
  return (
    <View testID={`reel-card-${card.cardId}`} className="flex-1 justify-end p-6">
      {card.tags.length > 0 ? (
        <Text testID="reel-card-tag" className="text-cyan-300">
          {card.tags.join(' / ')}
        </Text>
      ) : null}
      <Text testID="reel-card-name" className="text-2xl text-white">
        {card.product.title}
      </Text>
      <Text testID="reel-card-price" className="text-lg text-rose-200">
        ¥{card.product.priceYen.toLocaleString()}
      </Text>
      <Text testID="reel-card-pitch" className="text-white">
        {card.pitch}
      </Text>
      <Text testID="reel-card-label" accessibilityRole="text" className="text-cyan-200">
        {card.ownershipLabel.text}
      </Text>
      <View className="mt-4 flex-row gap-3">
        {/* スワイプ代替のボタン（A11y: NFR-A11Y-01） */}
        <Pressable testID="reel-action-debate" accessibilityLabel="買わない・論破する" onPress={onSwipeLeft}>
          <Text className="text-white">✕ 買わない</Text>
        </Pressable>
        <Pressable testID="reel-action-later" accessibilityLabel="あとで見る" onPress={onSwipeRight}>
          <Text className="text-white">→ あとで</Text>
        </Pressable>
        <Pressable
          testID="reel-action-buy"
          accessibilityLabel="Amazon で買う"
          onPress={onDoubleTap}
        >
          <Text className="text-white">🛍 Amazon で買う</Text>
        </Pressable>
      </View>
    </View>
  );
}

/** Amazon 遷移確認オーバーレイ（FR-REEL-05、mockup #buyOverlay の移植）。 */
function AmazonTransitionOverlay(props: {
  card: ReelCard;
  onConfirm: () => void;
  onCancel: () => void;
}): React.JSX.Element {
  const { card, onConfirm, onCancel } = props;
  return (
    <View testID="amazon-transition-overlay" className="absolute inset-0 justify-center bg-black/60 p-6">
      <View className="rounded-2xl bg-indigo-900 p-6">
        <Text className="text-white">Amazon に飛ばすよ</Text>
        <Text testID="overlay-amount" className="text-2xl text-rose-200">
          ¥{card.product.priceYen.toLocaleString()}
        </Text>
        <Pressable testID="overlay-confirm" accessibilityLabel="Amazon で買う" onPress={onConfirm}>
          <Text className="text-white">🛍 Amazon で買う</Text>
        </Pressable>
        <Pressable testID="overlay-cancel" accessibilityLabel="やめとく" onPress={onCancel}>
          <Text className="text-white">やめとく</Text>
        </Pressable>
      </View>
    </View>
  );
}
