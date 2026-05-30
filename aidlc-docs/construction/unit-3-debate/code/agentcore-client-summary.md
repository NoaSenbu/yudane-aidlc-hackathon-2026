# Unit-3 Debate — Mobile AgentCore Client 実装サマリ（Phase 1 Step 6）

> Phase 1 Step 6（Mobile AgentCore Client、Outside-In TDD）の実装結果。
>
> 参照: [Phase 1 Plan §1 Step 6](../../../plans/unit-3-debate-code-generation-phase1-plan.md) / [infrastructure-design §1 / §5](../infrastructure-design/infrastructure-design.md)
>
> 完了日: 2026-05-30 / 担当: Member B（AI 代行実装）/ TDD スタイル: Outside-In TDD

---

## 1. 生成ファイル

| ファイル | 役割 |
|---|---|
| `mobile/src/features/debate/types.ts`（70 行）| 共有型定義（EventType / DebateAxis / StrandsStreamEvent / DebateInvocationPayload）|
| `mobile/src/features/debate/agentcore-client.ts`（160 行）| LC-D-09 AgentCore Runtime 呼び出しクライアント |
| `mobile/src/features/debate/agentcore-client.test.ts`（200 行）| 7 unit tests（vitest + DI モック）|

---

## 2. API 仕様

### 2.1 `DebateAgentCoreClient`

```typescript
new DebateAgentCoreClient({
  runtimeEndpointArn: process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN ?? '',
  region: 'ap-northeast-1',
  fetchJwt: async () => (await Amplify.Auth.fetchAuthSession()).tokens?.idToken?.toString() ?? null,
});

for await (const chunk of client.invoke(payload)) {
  // chunk: Uint8Array（streaming raw bytes）または StrandsStreamEvent（error 時）
}
```

### 2.2 制御フロー

1. **設定検証**: `runtimeEndpointArn` が空なら `Error` を throw
2. **JWT 取得**: `fetchJwt()` で Cognito ID Token 取得 → null/empty で `auth.unauthenticated` event yield
3. **payload sanitize**: `actor_id` / `actorId` / `user_id` / `userId` を削除（SECURITY-08）
4. **HTTP POST**: `Authorization: Bearer <jwt>` ヘッダで invoke
5. **429 リトライ**: ThrottlingException で 1 回のみリトライ → 2 回目失敗で `runtime.throttled` event
6. **streaming**: `response.body.getReader()` で Uint8Array chunk を yield

---

## 3. テスト 7 ケース

| グループ | テストケース | 検証 |
|---|---|---|
| configuration | `runtimeEndpointArn` 空で throw | EAS Build で SSM 注入を強制 |
| JWT auth | `fetchJwt` で取得 + Bearer ヘッダ | Authorization 正しく設定 |
| JWT auth | JWT 取得失敗 → auth.unauthenticated | fail-safe |
| payload | actor_id を payload から除外 | SECURITY-08 三重保証 |
| streaming | chunk を Uint8Array で yield | streaming 正常動作 |
| retry | 429 で 1 回リトライ → success | PAT-D-COST-02 |
| retry | 2 回目失敗 → runtime.throttled error | コスト保護 |

**実行結果**: 7/7 green / 197ms。

---

## 4. 設計上の判断

### 4.1 Phase 1 では `@aws-sdk/client-bedrock-agentcore` の実 import を保留

**理由**:
- 依存解決時間（AgentCore SDK ≈ 30〜50 transitive deps）が長く、Phase 1 の疎通優先度を考慮
- AgentCore SDK の React Native 互換性（Hermes / Metro Bundler 設定）が未検証
- HTTP fetch + Cognito JWT Bearer 方式は infrastructure-design §1.1 の Cognito Authorizer 構成と直接整合

**互換性保証**: API シグネチャ `client.invoke(payload) → AsyncIterable<Uint8Array>` を維持し、Phase 2 で SDK に置換可能。テスト時の DI モック（`fetch`, `fetchJwt`, `abortController`）も SDK 切替時に再利用できる構造。

### 4.2 SECURITY-08 三重保証の最終層（Mobile クライアント側）

| レイヤ | 保証 |
|---|---|
| **Pydantic（Backend）** | `extra='ignore'` で actor_id 破棄（Step 3）|
| **debate_handler（Backend）** | `parse_jwt_actor_id(context)` で context.user.sub のみ伝播（Step 5）|
| **agentcore-client（Mobile）** | `sanitizePayload()` で actor_id 派生 4 キー（actor_id/actorId/user_id/userId）を明示削除（Step 6） |

3 層で攻撃者の偽装を破棄。テスト `test_actor_id_is_excluded_from_payload` で明示検証。

### 4.3 EAS Build 時の SSM 環境変数注入（4IDC-1 修正）

```javascript
// mobile/app.config.js（Phase 5 で本格対応、Phase 1 ではテスト用 dummy）
export default ({ config }) => ({
  ...config,
  extra: {
    EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN: process.env
      .EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN,
  },
  hooks: {
    postPublish: [
      // EAS Build 時に aws ssm get-parameter で SSM 値を取得
    ],
  },
});
```

Mobile は **SSM API への直接アクセス権を持たない**（Cognito Identity Pool 不採用）。代わりに EAS Build 時に CI 経由で SSM 値を取得し、`EXPO_PUBLIC_*` 環境変数として bundle に埋め込む。値変更時は **再ビルド + OTA 更新** が必要（決勝前カナリアリリースのフローで対応、infrastructure-design §5 で確定済み）。

### 4.4 Phase 2 への引き継ぎ

| 項目 | Phase 2 で対応 |
|---|---|
| `@aws-sdk/client-bedrock-agentcore` への置換 | API シグネチャを維持したまま内部実装を `InvokeAgentRuntimeCommand` に置換 |
| `runtimeSessionId` の発行 | Mobile 側で `ULID + actor_id` で 63 文字以下の session ID を発行（business-rules STREAM-03）|
| `client_session_id` 発番ロジック | Mobile UI 層で論破セッション開始時に発番、payload に含めて送信 |
| Token Refresh ハンドリング | JWT 期限切れ時に Amplify Auth.fetchAuthSession() を再呼び出しして再試行 |
| `app.config.js` Expo Plugin | EAS Build 時の SSM 値取得を Plugin 化 |

---

## 5. ハッカソン評価軸へのインパクト

- **Unit 分解の適切さ**: Mobile / Backend で別言語（TS / Python）でも同じ DTO 構造を共有、SECURITY-08 三重保証の各層が独立してテスト可能
- **創造性とテーマ適合性**: Cognito JWT Bearer 認証のシンプルさを維持しつつ、`runtimeEndpointArn` 経由で staging/prd 切替を物理層で実現
- **ドキュメント品質**: TDD サイクル全段（Red → Green → Refactor → DI パターン）を 7 テストで明示
- **AI-DLC プロセス**: Outside-In TDD（外側 fetch から内側 sanitize へ）で UI 層 → ネットワーク層 → ドメイン層の順で構築、Phase 2 の DebateScreen 実装に直結
