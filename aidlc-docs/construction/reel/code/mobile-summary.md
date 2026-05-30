# Unit-4 Reel — Code Summary: Mobile（Step 6〜8）

> `mobile/src/features/reel/` のフロントエンド生成サマリ。Outside-In TDD（純ロジックは vitest + fast-check、画面は TDD 例外の機械的移植）。
> 確定方針: FD/NFR/Infra 全ステージ確定済み + 矛盾解消反映済み

## 生成物（`mobile/src/features/reel/`）

| ファイル | 役割 | テスト |
|---|---|---|
| `types.ts` | Reel ビュー型（ReelCard / ReelPage / ExpAward 等） | 型のみ（TDD 例外）|
| `gestures.ts` | `resolveGesture`（ALG-GESTURE 純関数、閾値/優先順位/遷移ガード） | `gestures.test.ts`（example 8）+ `gestures.pbt.test.ts`（PBT 3）|
| `boost-nudge.ts` | `shouldNudge`（深夜ブースト誘導アニメ判定、US-02-01 AC-2） | `boost-nudge.test.ts`（example 4）+ `boost-nudge.pbt.test.ts`（PBT 3）|
| `client-transition-id.ts` | `makeClientTransitionId`（冪等キー生成） | `client-transition-id.test.ts`（example + PBT）|
| `reel-api.ts` | `fetchReel` / `recordAmazonTransition`（M-12 経由 I/O、DI） | `reel-api.test.ts`（fake client）|
| `use-reel-feed.ts` | `useReelFeed`（TanStack useInfiniteQuery カーソルページング） | ロジックは reel-api.test でカバー |
| `use-amazon-redirect.ts` | `useAmazonRedirect`（確認後 → 遷移記録 → Deep Link、冪等キー） | ロジックは reel-api / client-transition-id でカバー |
| `reel-screen.tsx` | M-03 画面（FlatList pagingEnabled + GestureLayer + 確認オーバーレイ + ボタン代替） | TDD 例外（mockup 機械的移植）|
| `index.ts` | feature 公開エクスポート | — |

## テスト分割方針（ユーザー要望反映）
- example テストと PBT を別ファイルに分割（`*.test.ts` / `*.pbt.test.ts`）
- `tech-typescript.md §10`「PBT は Unit Test と同居、プロパティ関数で区別」に沿い、ファイル分離でより明確化

## MSW（契約テスト土台）
- `mobile/src/test/msw-handlers.ts` に `GET /v1/reel` / `POST /v1/amazon-transitions` を追記（examples/reel.yaml 整合）

## アクセシビリティ（NFR-A11Y）
- スワイプ操作にボタン代替（`reel-action-debate` / `reel-action-later` / `reel-action-buy`、NFR-A11Y-01）
- `accessibilityLabel` / `accessibilityRole` 付与、`data-testid`（testID）で automation friendly

## 検証メモ
- 全 reel ファイル diagnostics 0
- **vitest 実行は Build and Test 段**（本ローカルに node_modules 未セットアップ、package-lock 未コミットのため install を保留。ユーザー合意済み）。CI `ci.yml` の frontend ジョブで実行
- `reel-screen.tsx` は React Native + NativeWind の機械的移植（TDD 例外 §12.3）。ロジックは別ファイルの純関数・フックでテスト済み
- EXP は遷移レスポンス（ExpAward）を楽観表示、確認オーバーレイは削除不可（FR-REEL-05）
