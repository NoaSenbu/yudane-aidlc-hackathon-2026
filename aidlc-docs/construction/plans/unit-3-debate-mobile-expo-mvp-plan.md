# Unit-3 Debate — Mobile Expo MVP Plan（Expo Go シミュレーター動作確認）

> **目的**: Phase 1〜4+6（AWS デプロイ非依存範囲）で完成した Unit-3 Debate を、**Mobile の Expo Go iOS シミュレーター**上で実機動作させる。Backend は `agentcore dev --port 8080` のローカルモードを併用し、実 Bedrock Haiku 4.5 でストリーミング論破を確認する（L2 構成）。
>
> 参照: [Phase 2 Plan](./unit-3-debate-code-generation-phase2-plan.md) / [Phase 3+4+6 Plan](./unit-3-debate-code-generation-phase3-6-plan.md) / [Direction D Design System](../design-system/direction-d-design-system.md) / [frontend-design.md](../unit-3-debate/functional-design/frontend-design.md) / [local-dev-guide.md](../unit-3-debate/code/local-dev-guide.md)
>
> 作成: 2026-05-30 / 担当: AI 代行実装 / Phase: ★★ B-309 backlog の MVP 取り出し（Expo Go 範囲のみ）★★
>
> ユーザー指示確定（2026-05-30）:
> - **Q1=C**: Expo Go から（必要に応じて Dev Client へ移行）
> - **Q2=B**: Direction D D-1（リール風）+ D-2 + D-3 を React Native に移植
> - **Q3**: Backend 起動（AWS 認証情報含む）も AI で実施

---

## 0. このプランの位置づけ

### 0.1 既存資産

Phase 1〜2+3+4+6 で既に**純ロジック層は完成**している:

| 層 | ファイル | 状態 |
|---|---|---|
| AgentCore Client | `mobile/src/features/debate/agentcore-client.ts` | ✅ 完成（IAM SigV4 + JWT） |
| Event Parser | `mobile/src/features/debate/event-parser.ts` | ✅ 完成（NDJSON 変換、Phase 3 で moderation_blocked / graceful_shutdown_initiated 追加） |
| DebateViewModel | `mobile/src/features/debate/screens/debate-view-model.ts` | ✅ 完成（純関数 reducer） |
| AffirmViewModel | `mobile/src/features/debate/screens/affirm-view-model.ts` | ✅ 完成 |
| Direction D Labels | `mobile/src/features/debate/screens/direction-d-labels.ts` | ✅ 完成（軸 → ラベル SSOT） |
| Telemetry | `mobile/src/features/debate/telemetry.ts` | ✅ 完成（10 イベント） |
| Zustand Store | `mobile/src/features/debate/store/debate-store.ts` | ✅ 完成 |

**未完成**:

- React Native ランタイム（Expo / `react-native` / NativeWind v4 / React Navigation）が **mobile/package.json に未導入**
- 全 React Native コンポーネント（`<DebateScreen>` / `<AffirmScreen>` / `<ReelScreen>` 等の View レイヤ）
- Backend ローカル起動環境（AWS 認証情報 + Bedrock モデル承認 + Python 依存）

### 0.2 範囲定義

**含む**:

- Mobile に Expo SDK 52 + React Native 0.76 + NativeWind v4 + React Navigation を初導入
- Direction D Atom コンポーネント 5 種（`<DPanel>` / `<DPill>` / `<DRule>` / `<DCta>` / `<DSeal>`）
- Direction D Screen 3 種（D-1 ReelScreen / D-2 DebateScreen / D-3 AffirmScreen）
- ナビゲーション（Reel → Debate → Affirm の遷移）
- AgentCore Client にローカルモード分岐追加（HTTP 直接 + JWT バイパス）
- Backend ローカル起動環境セットアップ（AWS 認証情報 + Bedrock モデル承認確認 + Python 依存 install）
- iOS シミュレーター上での動作確認シナリオ
- ReelScreen からの起動 trigger は `'reel_skip'` 固定（`'cart_intercept'` / `'product_dwell'` は Cart Intercept Share Extension / 商品詳細画面が必要なため範囲外、m1 修正）

**含まない**（Expo Dev Client / EAS Build 移行時に着手）:

- Cart Intercept Share Extension（iOS Native Module 必要、Q2=B 範囲外）
- Cognito 認証 UI（既存 `mobile/src/features/auth/` に実装済の onboarding-store を流用するが画面化はせず、`local-user` 固定）
- 通知（Push Notification、End User Messaging）
- カレンダー連動（Unit-6 範囲）
- D-4〜D-8 画面（Notif / Home / Watchlist / Chat / Membership）

### 0.3 完了条件（Definition of Done）

- [ ] `cd backend && bash scripts/run_local.sh` で `agentcore dev` が `http://localhost:8080` で起動
- [ ] `cd mobile && npx expo start --ios` で iOS シミュレーターが起動し、ReelScreen が表示される
- [ ] ReelScreen の「論破されて買う」相当の左スワイプ or タップで DebateScreen に遷移
- [ ] DebateScreen で実 Bedrock Haiku 4.5 のストリーミング token が表示される
- [ ] 論破 I・データ / 論破 II・感想 / 論破 III・ご褒美 のラベル別に token が振り分けられる
- [ ] 90 秒タイマーが画面右上で減算する
- [ ] Agree CTA タップで AffirmScreen に遷移、`#503-XXXXXXX` 受領証が表示される
- [ ] Refuse CTA を 3 回連続でタップすると、4 回目の起動で `cooldown_triggered` イベントが返る
- [ ] vitest 既存 157 tests が **全 green を維持**（Phase 3+4+6 完了時点の 157 件、Mobile 19 ファイル / Phase 3+4+6 サマリ §4 累計参照）
- [ ] diagnostics エラー 0 件
- [ ] `aidlc-docs/construction/unit-3-debate/code/expo-mvp-summary.md` 新規作成

---

## 1. Step 一覧

| # | Step | 内容 | 担当層 | 依存 | 想定工数 |
|---|---|---|---|---|---|
| **A1** | Backend ローカル起動環境準備 | AWS 認証 / Bedrock 承認確認 / Python 依存 install / `.env.local` / 起動確認 | Backend + 環境 | なし | 1h |
| **A2** | Mobile Expo SDK 52 導入 | `package.json` に expo / react-native / @types/* 追加、`app.json` / `App.tsx` / `index.ts` 作成、Metro bundler 動作確認 | Mobile | A1 後でも独立可 | 1.5h |
| **A3** | NativeWind v4 + Direction D トークン | `tailwind.config.js` / `babel.config.js` / `metro.config.js` / `global.css` / フォント `Shippori Mincho` + `Cinzel` 同梱 | Mobile | A2 | 1.5h |
| **A4** | Atom コンポーネント 5 種 | `<DPanel>` / `<DPill>` / `<DRule>` / `<DCta>` / `<DSeal>` の RN 版実装 + Storybook 風サンプル画面 | Mobile | A3 | 1h |
| **A5** | AgentCore Client ローカルモード拡張 | `agentcore-client.ts` に `mode='local'` 分岐追加、HTTP 直接 + JWT バイパス、既存 vitest を維持 | Mobile | A2（既存 client は workspace 内にある）| 0.5h |
| **A6** | D-1 ReelScreen 実装 | リール風 + 商品カード + 「論破されて買う」CTA、Direction D 黒 × 金で SSOT HTML から移植 | Mobile | A4 | 1.5h |
| **A7** | D-2 DebateScreen 実装 | 既存 `debate-view-model` 結線 + 90 秒タイマー UI + 軸別 token 表示 + Agree / Refuse CTA | Mobile | A4, A5, view-model | 2h |
| **A8** | D-3 AffirmScreen 実装 | 既存 `affirm-view-model` 結線 + DSeal アニメ + 受領証 + 「Amazon で受け取る」 CTA | Mobile | A4, view-model | 1h |
| **A9** | React Navigation 結線 | Stack Navigator で Reel → Debate → Affirm、Affirm から Reel に戻る | Mobile | A6, A7, A8 | 0.5h |
| **A10** | iOS シミュレーター動作確認 | `expo start --ios` 起動 + 動作確認シナリオ実行 + バグ修正 | Mobile + Backend | 全 Step | 1.5h |
| **A11** | サマリ文書 + state 更新 | `expo-mvp-summary.md` + `aidlc-state.md` + `audit.md` 追記 | docs | 全 Step | 0.5h |

**合計想定工数**: 約 11.5 時間（1.5〜2 日相当の AI 連続実装）

---

## 2. Step A1: Backend ローカル起動環境準備

### 2.1 確認 / 整備項目

- [ ] **Python 仮想環境 activate**: `pyenv shell hackson` または `pyenv activate hackson`（または `source ~/.pyenv/versions/3.13.2/envs/hackson/bin/activate`）で `which python` が `/Users/naganotakashiryou/.pyenv/versions/3.13.2/envs/hackson/bin/python3.13` を返すことを確認
- [ ] **AWS 認証情報**: `aws sts get-caller-identity` で apne1 アクセス可能を確認。未設定なら `aws configure` で `~/.aws/credentials` に設定（ユーザーの ACCESS_KEY_ID / SECRET_ACCESS_KEY が必要、AI 側で値は生成しない）
- [ ] **Bedrock Claude Haiku 4.5 モデルアクセス**: `aws bedrock list-foundation-models --region ap-northeast-1` で `anthropic.claude-haiku-4-5` が含まれるか確認。**未承認の場合はユーザー側で AWS マネジメントコンソール → Bedrock → Model access からリクエスト承認が必要**（AI からは申請できない）
- [ ] **Python 依存 install**: `pip install bedrock-agentcore strands-agents`（pyenv hackson activate 状態で）
- [ ] **`.env.local` 作成**: `backend/.env.local` に `DEBATE_LOCAL_MODE=true` / `ENV_NAME=dev` / `AWS_REGION=ap-northeast-1` / `LOCAL_USER_ID=local-user`
- [ ] **★ `local_app.py` 新規作成**: `main.py` の `debate_handler` を **`BedrockAgentCoreApp` または `FastAPI`** でラップした ASGI app を `backend/src/debate/local_app.py` に作成（C1 修正、後述 §2.4）
- [ ] **`run_local.sh` 修正**: 既存スクリプトの `agentcore dev src/debate/main:app` 部分を `agentcore dev src/debate/local_app:app` に変更（後述 §2.5）
- [ ] **起動テスト**: `bash backend/scripts/run_local.sh` で起動 → 別ターミナルで curl テスト（`local-dev-guide.md §2.4`）

### 2.2 ブロッカー対応

| ブロッカー | 対処 |
|---|---|
| AWS 認証情報未設定 | ユーザーに `aws configure` 実施を依頼、またはユーザーから ACCESS_KEY_ID / SECRET_ACCESS_KEY を受け取って `~/.aws/credentials` に書き込み（**注: シークレット情報のため Slack 等での共有禁止、AI Chat 内で受け渡し**）|
| Bedrock モデル未承認 | ユーザーに AWS コンソール → Bedrock → Model access → Anthropic Claude Haiku 4.5 のリクエスト送信を依頼。承認は通常即時〜数分。**ブロッカーになる場合 Step A2 以降を先行**（ローカル UI 動作確認は Mock Backend で進める）|
| `bedrock-agentcore` パッケージが pypi 未公開の場合 | `pip install --no-deps` 試行 / FastAPI 直接 wrapper（`§2.4` の代替案）にフォールバック |

### 2.3 完了条件

- [ ] `bash backend/scripts/run_local.sh` で `INFO: Uvicorn running on http://0.0.0.0:8080` が出力される
- [ ] curl で `[FACT]` `[PSYCHOLOGY]` 含むストリーミング応答が確認できる

### 2.4 ★ `backend/src/debate/local_app.py` 新規作成（C1 修正）

`debate_handler(payload, context)` は AgentCore Runtime SDK のシグネチャで、FastAPI / uvicorn から直接呼べない。**ASGI app でラップ**する:

```python
# backend/src/debate/local_app.py（新規）
"""ローカル開発用の ASGI app wrapper。

`debate_handler(payload, context)` は AgentCore Runtime SDK 用のシグネチャ。
ローカル開発（`agentcore dev` または `uvicorn` 直接）では FastAPI でラップして
HTTP POST /invocations を受け付ける。

参照: aidlc-docs/construction/plans/unit-3-debate-mobile-expo-mvp-plan.md §2.4
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from backend.src.debate.local_mode import is_local_mode, local_parse_jwt_actor_id
from backend.src.debate.main import debate_handler

app = FastAPI(title="YUDANE Debate Local Dev Server")


@app.post("/invocations")
async def invocations(request: Request) -> StreamingResponse:
    """Mobile / curl からの POST /invocations を受け、debate_handler の async generator を NDJSON で返す。"""
    payload = await request.json()
    # ローカルモードでは context.user.sub を local-user 固定
    actor_id = local_parse_jwt_actor_id() if is_local_mode() else "anonymous"
    context = SimpleNamespace(user=SimpleNamespace(sub=actor_id))

    async def stream_body():
        async for event in debate_handler(payload, context):
            yield (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(stream_body(), media_type="application/x-ndjson")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

**依存追加**: `pip install fastapi uvicorn` を §2.1 に追加（`bedrock-agentcore` がこれらを transitively 持つ可能性あり、その場合は再インストール不要）。

### 2.5 `run_local.sh` 修正

```bash
# backend/scripts/run_local.sh の修正点
# Before: agentcore dev src/debate/main:app --port 8080
# After:  agentcore dev src/debate/local_app:app --port 8080

# uvicorn フォールバックも main → local_app に変更
# Before: python -m uvicorn src.debate.main:app --port 8080 --reload
# After:  python -m uvicorn backend.src.debate.local_app:app --port 8080 --reload --reload-dir backend/src
```

---

## 3. Step A2: Mobile Expo SDK 52 導入

### 3.1 追加する依存

```json
// mobile/package.json (Phase 4 で追加)
{
  "dependencies": {
    "expo": "~52.0.0",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "react-native": "0.76.5",
    "expo-status-bar": "~2.0.0",
    "expo-constants": "~17.0.0",
    "expo-font": "~13.0.0",
    "expo-splash-screen": "~0.29.0",
    "@expo-google-fonts/shippori-mincho": "^0.2.3",
    "@expo-google-fonts/cinzel": "^0.2.3",
    "react-native-safe-area-context": "4.12.0",
    "react-native-screens": "~4.4.0",
    "react-native-gesture-handler": "~2.20.0",
    "react-native-reanimated": "~3.16.1",
    "@react-navigation/native": "^7.0.0",
    "@react-navigation/native-stack": "^7.0.0",
    "nativewind": "^4.1.0",
    "tailwindcss": "^3.4.0"
  },
  "devDependencies": {
    "@babel/core": "^7.25.0",
    "@types/react": "~18.3.12"
  },
  "scripts": {
    "start": "expo start",
    "ios": "expo start --ios",
    "android": "expo start --android"
  }
}
```

注: `@types/react-native` は React Native 0.71+ で `react-native` パッケージに型同梱されたため不要（M5 修正）。

### 3.2 新規ファイル

| ファイル | 目的 |
|---|---|
| `mobile/app.json` | Expo メタ情報（name / slug / scheme / icon / splash）|
| `mobile/babel.config.js` | `babel-preset-expo` + `react-native-reanimated/plugin` + `nativewind/babel` |
| `mobile/index.ts` | Expo エントリ（`registerRootComponent(App)`）|
| `mobile/App.tsx` | Root Component（NavigationContainer + 初期 Stack）|
| `mobile/metro.config.js` | NativeWind / 既存 monorepo workspace 解決 |

### 3.3 既存 vitest との両立（M1 修正）

**問題**: NativeWind v4 / React Native を入れた瞬間、既存 vitest（純ロジック）が import エラーで壊れる可能性が高い。

**確認済み（Phase 3+4+6 完了時点）**: 既存 19 ファイル / 157 tests は **react-native を import していない純ロジック**（view-model / store / event-parser / agentcore-client / telemetry / e2e / integration）→ **`react-native` モジュールのモックは原則不要**。

**解決策**:

1. **既存 19 テストファイルが `react-native` を import しないように維持**: 新規追加するコンポーネント（`<DPanel>` 等）は **vitest ではなくシミュレーター動作確認のみ**で検証
2. **vitest.config.ts は最小限**: 既存通り node 環境でのみ実行（変更不要、または既存設定を踏襲）
3. **NativeWind v4 の type 解決**: `nativewind` の `className` prop の型エラーを抑止するため、`mobile/src/types/nativewind.d.ts` で型拡張（任意、tsc に影響あれば追加）

**Phase A2 完了条件**:

- [ ] **既存 157 tests が green を維持する**ことを最重要視
- [ ] RN コンポーネントテスト（`<DPanel>` 等）は **iOS シミュレーター動作確認**（人間確認）のみで済ませる
- [ ] React Native ランタイムを使うコンポーネントの vitest 化は **本 MVP の範囲外**（B-309 残作業として backlog 維持）

### 3.4 既存ファイルの保全

- 既存 `mobile/src/features/debate/`（純ロジック）のソースは **書き換えない**（agentcore-client は §6 で `localMode` オプションを追加するのみ、追記）
- 既存 `mobile/src/features/auth/` / `mobile/src/features/platform/` / `mobile/src/app/` も書き換えない（Expo 化に伴う必要最小限の調整のみ）
- 既存テスト 19 ファイル / 157 tests は **そのまま green を維持**

### 3.5 完了条件

- [ ] `npx expo start --ios` が起動し、iOS シミュレーターで「Hello YUDANE」相当の placeholder 画面が表示
- [ ] **既存 `npx vitest run` 157 tests 全 green**（最重要）
- [ ] `npx tsc --noEmit` エラー 0

---

## 4. Step A3: NativeWind v4 + Direction D トークン

### 4.1 NativeWind v4 設定

NativeWind v4 は **`metro.config.js` で `withNativeWind()` ラップ** + **`global.css` の import** が公式推奨パターン（v3 以前と異なる）:

```js
// mobile/metro.config.js
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

const config = getDefaultConfig(__dirname);

module.exports = withNativeWind(config, { input: './src/styles/global.css' });
```

```css
/* mobile/src/styles/global.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

```js
// mobile/babel.config.js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
    plugins: [
      'react-native-reanimated/plugin',  // 必ず最後
    ],
  };
};
```

```js
// mobile/tailwind.config.js
const { hairlineWidth } = require('nativewind/theme');

module.exports = {
  content: ['./App.tsx', './src/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // Direction D — 黒服のコンシェルジュ
        'd-bg': '#0B0B0D',
        'd-bg-2': '#14110A',
        'd-line': 'rgba(201,162,75,0.18)',
        'd-gold': '#C9A24B',
        'd-gold-2': '#E7CE8A',
        'd-gold-3': '#8E6F2E',
        'd-ink': '#F5F1E8',
        'd-ink-2': '#B8B0A0',
        'd-ink-3': '#7A7468',
      },
      fontFamily: {
        'd-serif': ['ShipporiMincho_400Regular'],
        'd-display': ['Cinzel_400Regular'],
      },
      borderRadius: {
        'd-panel': '4px',
        'd-cta': '3px',
      },
      borderWidth: {
        hairline: hairlineWidth(),
      },
    },
  },
  plugins: [],
};
```

```ts
// mobile/App.tsx の冒頭で global.css を import（必須）
import './src/styles/global.css';
```

### 4.2 フォント同梱

- `npx expo install @expo-google-fonts/shippori-mincho @expo-google-fonts/cinzel expo-font expo-splash-screen`
- `App.tsx` で `useFonts()` ロード、ロード完了まで Splash 維持

### 4.3 完了条件

- [ ] `tailwind.config.js` の `--d-*` トークンが NativeWind v4 のクラスとして使える（`<View className="bg-d-bg" />`）
- [ ] フォント `Shippori Mincho` / `Cinzel` がシミュレーターで反映される
- [ ] vitest で NativeWind を含むコンポーネントテストが通る（実機ビルドは不要）

---

## 5. Step A4: Atom コンポーネント 5 種

### 5.1 新規ファイル

```
mobile/src/features/debate/components/
├── d-panel.tsx        # 漆黒 + 金縁の panel
├── d-pill.tsx         # ピル型タグ（ACCEPTED · #503-... 等）
├── d-rule.tsx         # 1px 金 hairline ruler
├── d-cta.tsx          # 太い金グラデの CTA ボタン
├── d-seal.tsx         # 封蝋シール（AffirmScreen で 0.9s アニメ）
└── index.ts           # 公開
```

### 5.2 vitest 戦略

- Direction D Atom は React Native コンポーネントなので、vitest では「**プロパティが正しく渡る** + **className 文字列が組み立てられる**」レベルの最小テストに留める
- 視覚回帰は Step A10 のシミュレーター動作確認で人間検証

### 5.3 完了条件

- [ ] 5 Atom が `mobile/src/features/debate/components/` に存在し、`<DPanel>` でテストレンダリング可能
- [ ] vitest 既存 + 新規 5 tests 全 green

---

## 6. Step A5: AgentCore Client ローカルモード拡張

### 6.1 設計

既存 `agentcore-client.ts` は `runtimeEndpointArn` を取って AWS の API Gateway へ IAM SigV4 で接続する設計。ローカルモード分岐を追加:

```ts
// mobile/src/features/debate/agentcore-client.ts に追加
export interface DebateAgentCoreClientOptions {
  // 既存
  runtimeEndpointArn?: string;
  region: string;
  fetchJwt: () => Promise<string>;
  fetch?: typeof fetch;

  // Phase A5 新規追加
  /** ローカルモード（agentcore dev --port 8080 直接接続）。デフォルト false。 */
  localMode?: boolean;
  /** ローカルエンドポイント。`localMode=true` の場合に使用。デフォルト 'http://localhost:8080' */
  localEndpoint?: string;
}
```

`invoke()` メソッドの分岐:

```ts
async *invoke(payload: DebateInvocationPayload): AsyncIterableIterator<...> {
  if (this.options.localMode) {
    yield* this.invokeLocal(payload);  // 新規メソッド
  } else {
    yield* this.invokeCloud(payload);  // 既存ロジック
  }
}

private async *invokeLocal(payload: DebateInvocationPayload) {
  const url = `${this.options.localEndpoint ?? 'http://localhost:8080'}/invocations`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),  // JWT も SigV4 もなし、ローカル開発用
  });
  // 既存の reader.read() ループをそのまま流用
  ...
}
```

### 6.2 環境変数経由の設定（Expo SDK 50+ の標準: EXPO_PUBLIC_*）

C2 修正: Expo SDK 50+ の標準は `process.env.EXPO_PUBLIC_*` でビルド時インライン化される方式。`Constants.expoConfig?.extra` は二重管理になるため採用しない。

```ts
// mobile/src/features/debate/agentcore-client-factory.ts (新規)
export function createDebateClient(): DebateAgentCoreClient {
  const localMode = process.env.EXPO_PUBLIC_DEBATE_LOCAL_MODE === 'true';
  const localEndpoint = process.env.EXPO_PUBLIC_DEBATE_LOCAL_ENDPOINT ?? 'http://localhost:8080';
  return new DebateAgentCoreClient({
    region: 'ap-northeast-1',
    fetchJwt: async () => 'dummy-jwt',
    localMode,
    localEndpoint,
  });
}
```

`.env` ファイル（`mobile/.env`、`.gitignore` 対象）:

```bash
EXPO_PUBLIC_DEBATE_LOCAL_MODE=true
EXPO_PUBLIC_DEBATE_LOCAL_ENDPOINT=http://localhost:8080
```

iOS シミュレーターは `localhost` で host にアクセス可能。Android Emulator は `10.0.2.2`、実機は host の LAN IP に書き換える。

### 6.3 完了条件

- [ ] `agentcore-client.ts` に `localMode` オプション追加、既存テスト 7 件全 green
- [ ] 新規追加テスト 3 件（localMode=true → fetch 呼び出し検証 / SigV4 skip / JWT bypass）

---

## 7. Step A6: D-1 ReelScreen 実装

### 7.1 設計

SSOT HTML の `ReelD` 関数を React Native + NativeWind v4 で再現:

- 縦型スワイプ: **Expo Go 互換のため `FlatList` の `pagingEnabled` + `snapToInterval` で簡易実装**（M2 修正、`react-native-pager-view` は Dev Client 必要なため避ける）
- 商品カード（モック商品 5 件、ASIN ハードコード）
- 「論破されて買う」CTA → DebateScreen へ navigate (`navigation.navigate('Debate', { asin, trigger: 'reel_skip' })`)

### 7.2 モック商品データ

```ts
// mobile/src/features/debate/screens/reel-mock-products.ts
export const mockProducts = [
  { asin: 'B0CK1RYW1Y', name: 'Sony WF-1000XM6', price: 49800, imageColor: 'bg-d-gold' },
  { asin: 'B0CCK67QH3', name: 'Anker Soundcore Sleep A20', price: 14990, imageColor: 'bg-d-gold-3' },
  { asin: 'B01ABC1234', name: 'BOSE QuietComfort Ultra', price: 39600, imageColor: 'bg-d-ink-3' },
  // ... 5 件
];
```

### 7.3 完了条件

- [ ] 5 商品が縦型スワイプ（FlatList paged）で切り替わる
- [ ] 「論破されて買う」CTA タップで DebateScreen に遷移、`route.params.asin` で受け取れる

---

## 8. Step A7: D-2 DebateScreen 実装（コア）

### 8.1 設計

既存 `debate-view-model.ts` の `reduceDebateView` を `useReducer` 経由で結線。**unmount 時は AbortController でストリーミングを中断**（M3 修正）:

```tsx
// mobile/src/features/debate/screens/debate-screen.tsx
export function DebateScreen({ route, navigation }: Props) {
  const asin = route.params.asin;
  const [viewState, dispatch] = useReducer(reduceDebateView, buildInitialDebateView());
  const client = useMemo(() => createDebateClient(), []);

  // セッション開始（mount 時）
  useEffect(() => {
    const abortController = new AbortController();
    let cancelled = false;

    dispatch({ type: 'session_started', asin, trigger: 'reel_skip', startedAt: new Date() });

    // ストリーミング起動
    (async () => {
      try {
        for await (const chunk of client.invoke(
          { user_input: 'でも欲しい', asin, trigger: 'reel_skip' },
          { signal: abortController.signal },  // M3: AbortController で中断
        )) {
          if (cancelled) break;
          if (chunk instanceof Uint8Array) {
            // event-parser に流す（buffering 内蔵）
            for await (const event of parseEventStream(asyncOnce(chunk))) {
              if (cancelled) break;
              dispatch({ type: 'stream_event', event });
            }
          }
        }
      } catch (err) {
        if (!cancelled && (err as Error).name !== 'AbortError') {
          dispatch({ type: 'stream_event', event: { type: 'error', metadata: { reason: 'stream.failed' } } });
        }
      }
    })();

    return () => {
      cancelled = true;
      abortController.abort();
    };
  }, [asin, client]);

  // 90 秒タイマー
  useEffect(() => {
    const interval = setInterval(() => dispatch({ type: 'tick', now: new Date() }), 1000);
    return () => clearInterval(interval);
  }, []);

  // Agree タップ → AffirmScreen へ
  const handleAgree = () => navigation.navigate('Affirm', { asin });

  return (
    <SafeAreaView className="flex-1 bg-d-bg">
      <DebateHeader timer={viewState.remainingSeconds} />
      <ItemCard asin={asin} />
      <DPanel>
        <CounselBlock label={viewState.factLabel} tokens={viewState.factTokens} />
        <DRule />
        <CounselBlock label={viewState.psychologyLabel} tokens={viewState.psychologyTokens} />
        {viewState.rewardTokens.length > 0 && (
          <>
            <DRule />
            <CounselBlock label={viewState.rewardLabel} tokens={viewState.rewardTokens} />
          </>
        )}
      </DPanel>
      <DCta disabled={!viewState.canAgree} onPress={handleAgree}>
        論破されたので買う
      </DCta>
    </SafeAreaView>
  );
}
```

注: `client.invoke()` の signature を `{ signal?: AbortSignal }` を受け取るよう Step A5 で拡張する（M3 修正）。

### 8.2 タイピング演出（簡易版）

Phase A7 では「token を受信したら全文表示」の最小実装。1 文字ずつタイピングは Phase A10 完了後の polish フェーズで対応（B-309 残作業）。

### 8.3 完了条件

- [ ] DebateScreen mount 時に Backend を呼び、ストリーミング token が表示される
- [ ] 軸別ラベルが正しく表示される
- [ ] 90 秒タイマーが動作（残時間が画面右上に減算表示）
- [ ] Agree CTA で AffirmScreen に遷移
- [ ] cooldown_triggered イベントで sessionStatus が 'cooldown' に切替、CTA 不活性

---

## 9. Step A8: D-3 AffirmScreen 実装

### 9.1 設計

既存 `affirm-view-model.ts` の `buildAffirmViewModel` を結線:

```tsx
export function AffirmScreen({ route, navigation }: Props) {
  const affirmVm = useMemo(
    () => buildAffirmViewModel({
      asin: route.params.asin,
      sessionId: 'sess-' + Date.now(),
      now: () => new Date(),
      serviceRecordIdGenerator: randomServiceRecordId,
    }),
    [route.params.asin]
  );

  return (
    <SafeAreaView className="flex-1 bg-d-bg justify-center items-center">
      <DPill>{affirmVm.acceptedPillText}</DPill>
      <DSeal />  {/* 封蝋アニメ 0.9s */}
      <Text className="font-d-serif text-d-ink text-3xl mt-8">{affirmVm.headlineText}</Text>
      <Text className="font-d-serif text-d-ink-2 text-base mt-4">
        正しい判断だと思いますよ。{'\n'}面倒な手配は、こっちでやっときます。
      </Text>
      <DCta onPress={() => Linking.openURL(`https://amazon.co.jp/dp/${route.params.asin}?tag=yudane-22`)}>
        Amazon で受け取る
      </DCta>
      <Text className="font-d-serif text-d-ink-3 text-sm mt-12">
        そんな感じなんで、おやすみなさい。
      </Text>
    </SafeAreaView>
  );
}
```

注（m2 修正）: 「Amazon で受け取る」CTA は `Linking.openURL()` で実 Amazon に遷移する（Associates Special Link の `?tag=yudane-22` 付き）。MVP では `tag` の値はモック（実際の Tracking ID は `tech-stack-decisions.md` で確定後）。

### 9.2 完了条件

- [ ] AffirmScreen が「ACCEPTED · #XXX-XXXXXXX」を表示
- [ ] DSeal アニメが 0.9s で再生される（reanimated）
- [ ] 「Amazon で受け取る」CTA で `Linking.openURL()` で実 Amazon が開く（または iOS シミュレーターで Safari が開く）

---

## 10. Step A9: React Navigation 結線

### 10.1 構造

```ts
// mobile/App.tsx
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator<{
  Reel: undefined;
  Debate: { asin: string };
  Affirm: { asin: string };
}>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Reel"
        screenOptions={{
          headerStyle: { backgroundColor: '#0B0B0D' },
          headerTintColor: '#F5F1E8',
          headerTitleStyle: { fontFamily: 'Cinzel_400Regular' },
        }}
      >
        <Stack.Screen name="Reel" component={ReelScreen} options={{ title: 'お見立て' }} />
        <Stack.Screen name="Debate" component={DebateScreen} options={{ title: '迷い、論破します' }} />
        <Stack.Screen name="Affirm" component={AffirmScreen} options={{ title: '承りました' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

---

## 11. Step A10: iOS シミュレーター動作確認

### 11.1 動作確認シナリオ

| シナリオ | 必須 / Bonus | 期待結果 |
|---|---|---|
| **A. 翻意フロー（必須）** | ★★ 必須 | ReelScreen で BOSE 商品を表示 → 「論破されて買う」タップ → DebateScreen でストリーミング token 表示 → 60 秒経過 → Agree タップ → AffirmScreen で受領証表示 |
| **B. クールダウン（必須）** | ★★ 必須 | ReelScreen → DebateScreen → Refuse 3 回タップ → 4 回目の起動で sessionStatus='cooldown' で CTA 全不活性 |
| **C. graceful shutdown（Bonus）** | ☆ 任意 | DebateScreen 起動 → 80 秒経過 → graceful_shutdown_initiated 表示 → session_complete reason='graceful_timeout'。**実 LLM の応答時間に依存するため、観測できれば bonus** |
| **D. moderation_blocked（Bonus）** | ☆ 任意 | Backend で NG-6 を含む応答が**偶発的に生成された場合のみ**観察可能。プロンプトインジェクション風の入力で誘発可能性あり |

### 11.2 既知の制約（Expo Go）

| 項目 | 制約 | 影響 |
|---|---|---|
| Cart Intercept Share Extension | Expo Go 不可（ネイティブモジュール必要）| Q2=B 範囲外、ReelScreen から直接遷移で代替 |
| Push 通知 | Expo Go では制限あり | NotifD 画面は今回スキップ |
| Cognito MFA UI | 既存 onboarding-store 使わず固定 `local-user` | 認証 UI なし、JWT バイパス |
| 実 DDB / Memory | LocalCooldownStore / LocalMemoryStore（in-memory dict）| プロセス再起動でリセット |

---

## 12. Step A11: サマリ文書 + state 更新

### 12.1 新規 / 更新ファイル

- [ ] **新規**: `aidlc-docs/construction/unit-3-debate/code/expo-mvp-summary.md`（Step A1〜A10 のサマリ + 動作確認シナリオ + 残作業 = 本格実装版 B-309 の差分）
- [ ] **更新**: `aidlc-docs/aidlc-state.md` に「Expo MVP 完成」マーカー追記
- [ ] **更新**: `aidlc-docs/audit.md` に Phase A1〜A11 の実施記録
- [ ] **更新**: `doc/backlog.md` の B-309 を末尾に「**ステータス: Expo Go MVP 完成（2026-05-30）**」を追記（structure.md §6.1 の運用ルールに従い、エントリ自体は**削除しない**。本格 Dev Client 移行と Cart Intercept Share Extension は引き続き backlog 残置）

---

## 13. リスクと緩和策

| ID | リスク | 影響度 | 緩和策 |
|---|---|---|---|
| R1 | NativeWind v4 が React Native 0.76 + Expo SDK 52 と非互換 | 高（A3 全体停止）| `nativewind@^4` 公式互換マトリクス確認、互換性問題が出たら StyleSheet API 直書きにフォールバック |
| R2 | vitest が Expo / RN モジュールを解決できない（既存テスト 157 件が壊れる）| 高（A2 全体停止）| `vitest.config.ts` に `alias` で react-native を `node-mock` 化、または `setupFiles` でグローバルモック追加 |
| R3 | Bedrock Claude Haiku 4.5 のモデルアクセス未承認 | 高（A1 ブロッカー）| ユーザーに AWS コンソール承認を依頼、承認待ちの間は A2〜A9 を先行 |
| R4 | Expo Go の React Native Reanimated バージョン制約 | 中（A8 DSeal アニメ）| Reanimated 不要なシンプル opacity アニメに代替（`Animated` API 標準）|
| R5 | Mobile workspace 内の monorepo パス解決（`shared/schema` 等）| 中（A2 build エラー）| `metro.config.js` で `watchFolders` 拡張、`tsconfig.json` の `paths` を Metro と連動 |
| R6 | iOS シミュレーターからの `localhost:8080` 接続不可 | 低（既知問題）| iOS シミュレーターは host の localhost が見えるので OK。実機 / Android は `EXPO_PUBLIC_DEBATE_LOCAL_ENDPOINT` を host IP に変更 |
| R7 | フォント（Shippori Mincho / Cinzel）のロード時間でスプラッシュが長引く | 低 | Splash Screen を維持し、ロード完了で hide。ロード失敗時は system font フォールバック |

---

## 14. ハッカソン評価軸へのインパクト

| 評価軸 | Expo Go MVP 完成による積み増し |
|---|---|
| **ビジネス意図の明確さ** | iOS シミュレーターで「過労気味リモートワーカーが 1 分で論破される」体験を**実機操作で**示せる、デモ説得力が桁違いに上がる |
| **Unit 分解の適切さ** | Mobile（コンポーネント）/ Backend（Strands Agent）/ Infra（CDK Snapshot）の 3 層分割が iOS シミュレーターで実証 |
| **創造性とテーマ適合性** | Direction D 黒服コンシェルジュの世界観が iOS シミュレーターで体験可能、HTML プロトタイプから実機操作感へ昇華 |
| **ドキュメント品質** | Plan + 多巡セルフレビュー + サマリで AI-DLC ワークフロー継続 |
| **AI-DLC プロセス実践** | 既存 363 tests を維持しつつ Expo MVP を追加、TDD + AI-DLC の併用例 |

---

## 15. 完了条件チェックリスト（Definition of Done）

### 15.1 機能

- [ ] iOS シミュレーターで `npx expo start --ios` 起動成功
- [ ] ReelScreen → DebateScreen → AffirmScreen の通し動作確認
- [ ] 実 Bedrock Haiku 4.5 のストリーミング token が DebateScreen に表示
- [ ] 軸別ラベル（論破 I・データ / II・感想 / III・ご褒美）に振り分け表示
- [ ] 90 秒タイマー減算
- [ ] Refuse 3 回 → cooldown_triggered で CTA 不活性
- [ ] AffirmScreen で受領証表示

### 15.2 品質ゲート

- [ ] vitest 既存 157 + 新規 8〜10 = **165〜167 tests all green**（回帰なし）
- [ ] `npx tsc --noEmit` エラー 0
- [ ] eslint は既存 workspace 設定を踏襲。React Native / Expo 用のルール追加は本 MVP の範囲外（重大な lint エラーが出た場合のみ修正、エラー 0 を絶対条件にしない、m5 修正）
- [ ] diagnostics エラー 0

### 15.3 ドキュメント

- [ ] `expo-mvp-summary.md` 新規作成
- [ ] `aidlc-state.md` 更新
- [ ] `audit.md` 更新
- [ ] `doc/backlog.md` の B-309 ステータス更新

---

## 16. 次フェーズ（本 Plan の対象外）

| 項目 | 対象 | 担当 |
|---|---|---|
| Cart Intercept Share Extension | Expo Dev Client + EAS Build 移行後 | Member D（Unit-5 範囲）|
| Cognito MFA 認証 UI | 既存 `mobile/src/features/auth/` 結線 | Member A |
| 実 dev 環境統合（Phase 1 Step 8）| AWS 認証 + EAS Build + 実機ビルド | Member A |
| 性能テスト 同時 100 セッション（Phase 6 T6.3）| 実 dev 環境必要 | Member B |
| 本格 RuntimeEndpoint canary deploy（Phase 5）| AWS デプロイ前提 | Member A |
| D-4〜D-8 画面（Notif / Home / Watchlist / Chat / Membership）| 各 Unit の責務 | 各 Member |

---

## 17. 参照

- [Direction D Design System](../design-system/direction-d-design-system.md)
- [frontend-design.md](../unit-3-debate/functional-design/frontend-design.md)
- [Phase 1 Plan](./unit-3-debate-code-generation-phase1-plan.md)
- [Phase 2 Plan](./unit-3-debate-code-generation-phase2-plan.md)
- [Phase 3+4+6 Plan](./unit-3-debate-code-generation-phase3-6-plan.md)
- [local-dev-guide.md](../unit-3-debate/code/local-dev-guide.md)
- [B-309 backlog](../../../doc/backlog.md)
