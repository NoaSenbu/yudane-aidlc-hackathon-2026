# Unit-3 Debate — debate-stack 実装サマリ（Phase 1 Step 1）

> Phase 1 Step 1（Infra Snapshot TDD）の実装結果。
>
> 参照: [Phase 1 Plan §1 Step 1](../../../plans/unit-3-debate-code-generation-phase1-plan.md) / [infrastructure-design.md](../infrastructure-design/infrastructure-design.md) / [tech-cdk.md](../../../../.kiro/steering/tech-cdk.md)
>
> 完了日: 2026-05-30 / 担当: Member B（AI 代行実装）/ TDD スタイル: Snapshot TDD

---

## 1. 生成ファイル

| ファイル | 役割 |
|---|---|
| `infra/lib/debate-stack.ts`（新規 245 行）| Unit-3 Debate のスタック定義 |
| `infra/test/debate-stack.test.ts`（新規 108 行）| Snapshot TDD のテスト 9 ケース |
| `infra/test/__snapshots__/debate-stack.test.ts.snap`（自動生成）| CloudFormation テンプレート fixture |
| `infra/bin/app.ts`（修正）| `DebateStack` を `debate-${env}-stack` で登録 |
| `backend/src/debate/__init__.py`（新規）| AgentCore Runtime コードアセット用 placeholder |
| `backend/src/debate/requirements.txt`（新規）| Phase 1 skeleton（Phase 2 で bundling） |

---

## 2. CDK 構成（実 AWS リソース）

### 2.1 採用したコンストラクト

| Construct | 種別 | 採用理由 |
|---|---|---|
| `aws_bedrockagentcore.Runtime` | L2 | `aws-cdk-lib` v2.170+ で安定提供。型安全 + grant ヘルパー利用可 |
| `aws_bedrockagentcore.Memory` | L2 | `MemoryStrategy.usingUserPreference()` / `usingSemantic()` の factory が整備済み |
| `aws_bedrockagentcore.RuntimeEndpoint` | L2 | `agentRuntimeId` 直接渡しで型安全 |
| `aws_bedrock.CfnGuardrail` | L1 | L2 が未整備のため CFN 直接（infrastructure-design §3.1 例と一致） |
| `aws_dynamodb.Table` | L2 | Unit-1 platform-stack と同パターン |

> Phase 1 計画書 §7 リスク 1 の「L1（`CfnRuntime`）でフォールバック準備」は **不要と判断**（L2 が apne1 で利用可能）。L2 採用は Phase 2 以降の grant ヘルパー再利用にも有利。

### 2.2 Unit-1 platform-stack からの SSM 参照（5 個）

| SSM Key | 参照先（debate-stack 内）|
|---|---|
| `/yudane/<env>/platform/kms-key-arn` | `kms.Key.fromKeyArn` で `IKey` 復元 → DDB / Memory 暗号化キー |
| `/yudane/<env>/platform/alerts-topic-arn` | `sns.Topic.fromTopicArn` で復元（Phase 6 Alarm 用、Phase 1 では Construct 化のみ）|
| `/yudane/<env>/platform/userpool-id` | `cognito.UserPool.fromUserPoolId` で復元 → Cognito Authorizer |
| `/yudane/<env>/platform/userpool-client-id` | `cognito.UserPoolClient.fromUserPoolClientId` で復元 |
| `/yudane/<env>/platform/auditlogger-layer-arn` | **Phase 1 では未参照**（Phase 2 で Lambda Layer 復元、Strands Agent IAM Role に attach） |

### 2.3 SSM 出力（6 個、Phase 1 範囲）

| Parameter Name | 既定値 | 用途 |
|---|---|---|
| `/yudane/<env>/debate/runtime-arn` | （CDK token） | Backend / 運用者参照 |
| `/yudane/<env>/debate/memory-id` | （CDK token） | Unit-7 削除バッチ |
| `/yudane/<env>/debate/runtime-endpoint-live-arn` | （CDK token） | EAS Build 時に環境変数注入 |
| `/yudane/<env>/debate/cooldowns-table-arn` | （CDK token） | Unit-7 Safeguard Stack 参照 |
| `/yudane/<env>/debate/model-id` | `anthropic.claude-haiku-4-5` | Strands Agent 起動時 1 回 GetParameter |
| `/yudane/<env>/debate/kill-switch` | `disabled` | 緊急停止用、毎セッション開始時 GetParameter |

> Phase 3 で `memory-export-bucket-arn`、Phase 5 で `runtime-endpoint-canary-arn` を追加（合計 8 個）。

### 2.4 IAM Role（最小権限）

```
AssumeRole: bedrock-agentcore.amazonaws.com
Policy:
  ✅ Bedrock InvokeModel / InvokeModelWithResponseStream
     → 2 ARN ワイルドカード（claude-haiku-4-5* / claude-sonnet-4-6*）
     → cdk-nag IAM5 は理由コメント付き Suppression
  ✅ AgentCore Memory CreateEvent / GetLastKTurns / RetrieveMemories（grantWrite + grantRead）
  ✅ DDB Cooldowns RW（grantReadWriteData）
  ✅ KMS Encrypt/Decrypt（grantEncryptDecrypt）
  ✅ Bedrock ApplyGuardrail（attrGuardrailArn 限定）
  ✅ SSM GetParameter（model-id / kill-switch のみ）
  ✅ CloudWatch / X-Ray（Resource:* は AWS 制約上必須、Suppression 適用）
```

### 2.5 lifecycleConfiguration（タイマー二段の物理層）

```typescript
lifecycleConfiguration: {
  idleRuntimeSessionTimeout: Duration.seconds(120),  // Strands Agent 90s + 30s バッファ
  maxLifetime: Duration.seconds(120),                // microVM 強制終了
}
```

PAT-D-PERF-02 と business-rules カタログ §12 に整合。

---

## 3. Snapshot TDD（9 テストケース）

| # | テスト名 | アサーション |
|---|---|---|
| 1 | AgentCore Runtime 1 個 | `AWS::BedrockAgentCore::Runtime` count = 1, NetworkMode='PUBLIC' |
| 2 | RuntimeEndpoint live 1 個 | `AWS::BedrockAgentCore::RuntimeEndpoint` count = 1, Name='live' |
| 3 | Memory 1 個 + 組み込み 2 Strategy | EventExpiryDuration=90, UserPreferenceMemoryStrategy + SemanticMemoryStrategy 含む |
| 4 | DDB CooldownsTable | PAY_PER_REQUEST + PITR + TTL='ttl' + KMS |
| 5 | Bedrock Guardrail NG-1〜8 | 8 DENIED_TOPICS（illegal-activity / health-harm / discrimination / minor-targeting / mental-health / threat-or-guilt-coercion / personal-data-misuse / associates-violation） |
| 6 | IAM Bedrock 2 ARN ワイルドカード | `claude-haiku-4-5*` + `claude-sonnet-4-6*` |
| 7 | SSM 6 個出力 | runtime-arn / memory-id / runtime-endpoint-live-arn / cooldowns-table-arn / model-id / kill-switch |
| 8 | cdk-nag 未抑制エラー 0 件 | `findError('AwsSolutions-.*')` がゼロ |
| 9 | Snapshot fixture | `Template.fromStack(stack).toJSON()` を `toMatchSnapshot()` で固定 |

**実行結果**: 9/9 green（vitest run）/ Duration 472ms / cdk-nag 全クリア。

---

## 4. cdk-nag Suppression

理由コメント付きで明示的に許可：

| Suppression ID | 理由 |
|---|---|
| `AwsSolutions-IAM4`（Stack 全体）| CDK 自動生成リソースの AWS 管理ポリシー、MVP 許容 |
| `AwsSolutions-IAM5`（Stack 全体）| Memory grantWrite/grantRead と DDB grantReadWriteData の actor_id 単位絞り込みなし。コード側で namespace 強制（PAT-D-SEC-02） |
| `AwsSolutions-IAM5`（runtime-role）| Bedrock 2 ARN ワイルドカード（model-id 切替時の AccessDenied 防止）+ logs/cloudwatch/xray の Resource:* は AWS 制約上必須 |

---

## 5. Phase 2 への引き継ぎ事項

| 項目 | Phase 2 で対応 |
|---|---|
| `backend/src/debate/main.py` の最小実装 | Step 5 main.py 実装で追加（Phase 1 Step 5）|
| `backend/src/debate/requirements.txt` の bundling | `bundling: { image, command: 'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output' }` を `AgentRuntimeArtifact.fromCodeAsset` に追加 |
| AuditLogger Lambda Layer 取り込み | `lambda.LayerVersion.fromLayerVersionArn` で SSM `auditlogger-layer-arn` を復元 → Strands Agent IAM Role に attach |
| Bedrock Guardrails の Strands Agent への関連付け | `bedrock_kwargs.guardrailIdentifier` を Phase 3 で設定 |
| custom Memory Strategy `m1_m2_axis_extractor` | Phase 4 T4.2 で `memory.addMemoryStrategy()` を追加 |
| RuntimeEndpoint canary | Phase 5 で `liveEndpoint` と並列に追加 |
| Memory streamDeliveryResources（S3 Export）| Phase 3 T3.2 で追加（aws-cdk-lib L2 が対応次第、L1 fallback）|

---

## 6. 既知の問題（Phase 1 範囲外）

- **`infra/test/platform-stack.test.ts > cdk-nag の未抑制エラーがない` が fail**: stash 検証により Step 1 開始前から fail していたことを確認。Unit-1 完了時の commit 由来 or 後続の cdk-nag ルール追加によるもの。修正は Member A の Unit-1 後続改善 or 別 Issue 化（B-302 候補、`doc/backlog.md` 追記予定）。
- **`infra/bin/app.ts` の `aws-cdk-lib.aws_dynamodb.TableOptions#pointInTimeRecovery is deprecated` Warning**: 既存の platform-stack / auth-stack でも同じ警告。Unit-1 / Unit-2 / Unit-3 すべてで `pointInTimeRecoverySpecification` への移行は別作業（B-303 候補）。

---

## 7. ハッカソン評価軸へのインパクト

- **Unit 分解の適切さ**: Unit-3 の物理リソースが Unit-1 / Unit-2 と SSM 経由で疎結合に連携、cdk-nag green で CI 化準備完了
- **創造性とテーマ適合性**: Bedrock Guardrails で NG-1〜8 を 8 DENIED_TOPICS として実装、特に NG-6（脅迫・罪悪感強要）の滑落防止を物理層で担保
- **ドキュメント品質**: TDD サイクル（Red → Green → Refactor → Snapshot）の証跡が test ファイル + snapshot fixture + 本サマリで traceable
- **AI-DLC プロセス**: Phase 1 Plan §1 Step 1 の checklist を [x] で更新、AI が Plan に従って実装した証跡完備
