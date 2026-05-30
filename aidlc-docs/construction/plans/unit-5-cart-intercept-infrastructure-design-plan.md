# Unit-5 Cart Intercept — Infrastructure Design Plan

> AI-DLC Construction Phase / Per-Unit Loop / Infrastructure Design ステージ。
> Functional Design §3（cart-stack.ts）と NFR Design（19 パターン適用）を**統合**し、論理コンポーネント → 物理 AWS リソース → 環境別差異 → デプロイパイプラインを 1 文書に集約する。
>
> 参照:
> - [unit-5 functional-design.md §3](../unit-5-cart-intercept/functional-design/functional-design.md#3-infrastructureinfralibcart-stackts)（Stack 構成 / SSM / cdk-nag）
> - [unit-5 nfr-design-patterns.md](../unit-5-cart-intercept/nfr-design/nfr-design-patterns.md)（19 パターン）
> - [unit-5 logical-components.md](../unit-5-cart-intercept/nfr-design/logical-components.md)（Mermaid + 相互作用 3 パターン）
> - [unit-1 functional-design.md §3.2](../unit-1-platform/functional-design/functional-design.md)（PlatformStack の kmsKey / idempotencyKeysTable / idempotencyBucket）
> - [.kiro/steering/tech-cdk.md](../../../.kiro/steering/tech-cdk.md)（CDK 命名規則 / cdk-nag）

---

## 1. ステージ目的

Functional Design / NFR Design で論理レベルは確定済み。本ステージでは以下を**物理レベルで確定**する:

1. **Stack 命名 / 環境分離**: dev（個人 sandbox）/ prd の Stack 名・リソース ARN・SSM パス・タグ戦略
2. **Cross-Stack 依存解決**: PlatformStack / AuthStack / SafeguardStack からの参照方式（CFN Output? SSM? 直接 import?）
3. **Lambda 実装詳細**: Layer 戦略、SnapStart 適用 3 関数の publish 戦略、Reserved Concurrency 集計
4. **EventBridge Scheduler IAM**: One-time Schedule × N 件作成における権限境界 + Scheduler Group
5. **End User Messaging Push**: Application（旧 Pinpoint App）作成方針 + Channel（APNs/FCM）設定 + 環境変数注入
6. **CloudWatch / SNS 観測性パイプライン**: Alarms 5 系統 → SNS Topic → Slack 配送のトポロジ
7. **デプロイ順序とロールバック手順**: Unit-1 Platform → Unit-2 Auth → **Unit-5 Cart** の依存
8. **コスト・容量シミュレーション**: NFR §6.4 で確定済み試算の Stack ごと内訳化（IaC でタグ別請求対応）

---

## 2. 既確定事項のサマリ（再決定不要）

| 領域 | 確定値 | 出典 |
|---|---|---|
| Stack ファイル | `infra/lib/cart-stack.ts` | Functional Design §3.1 |
| 命名規約 | `yudane-{env}{-init}-{domain}-{resource}`（例: `yudane-dev-d-cart-watch-items`） | tech-cdk.md / Unit-1 整合 |
| DDB CartWatchItems | On-Demand / GSI1（status × createdAt） / KMS / TTL / PITR=prd / RemovalPolicy=prd:RETAIN | Functional Design §3.1 / data-model §1.4 |
| DDB NotificationLogs | On-Demand / GSI1（cartWatchItemId × sentAt） / KMS / TTL 90 日 | Functional Design §3.1 / data-model §2 |
| Lambda Runtime | Python 3.13 / ARM64 / 512MB / Timeout 60s（Lambda により異なる） | NFR Design Q3 |
| SnapStart 適用 | `cart_intake` / `cart_dismiss` / `notification_dispatcher` の 3 関数 | NFR Requirements Q4 = B' |
| Reserved Concurrency | `notification_dispatcher=50` / `cart_attack_scheduler_retry=10` / 他 = 共有 100 | NFR Design Q3 |
| EventBridge Scheduler | One-time Schedule（30m/6h/24h × 3 件 per item） + rate(15min) for retry batch | Functional Design Q4 / NFR Design Q4 |
| End User Messaging Push | UpdateEndpoint 方式（Q5 = C）/ APNs + FCM | Functional Design §1.3 |
| CloudWatch Alarms | 5 系統（DLQ depth / Notification 遅延 / Scheduler create_failed / Lambda Error / **retry_failed**） | Functional Design §3.3 + NFR §5.1 |
| SSM Parameter パス | `/yudane/{env}{/init?}/cart/...` | Functional Design §3.1 |
| cdk-nag suppressions | `AwsSolutions-IAM5`（mobiletargeting wildcard）/ `AwsSolutions-SQS3`（DLQ KMS） | Functional Design §3.2 |
| Property-Based Testing | Snapshot TDD + `template.hasResourceProperties` | Functional Design §0.1 |

**NFR Design 確定 19 パターン**は [nfr-design-patterns.md](../unit-5-cart-intercept/nfr-design/nfr-design-patterns.md) を本 Stack の implementation guide として継承。

---

## 3. 設問（推奨案 + 選択肢）

> **推奨案を盲信せず批判的再検証する**運用ルール（[AGENTS.md §2](../../../.kiro/steering/AGENTS.md)）に基づき、各設問は推奨案 + 根拠 + 代替案 + 想定リスクで提示する。

### 推奨案再検証ログ（2026-05-29、Plan v1 → v2 → v3）

#### v1 → v2（4 件修正）

| Q | 旧推奨 | **改訂後推奨** | 検出 Issue | 変更理由 |
|---|---|---|---|---|
| Q1 | A | A | 問題なし | — |
| Q2 | A | A | 問題なし | — |
| Q3 | B | B | 問題なし | — |
| **Q4** | B（Group 2 分離） | **A（default Group + Schedule 名 prefix）** | 中：FD §3.2 cdk-nag IAM Resource ARN `schedule/default/cart-*` と整合不一致、Group 分離は ARN 全書換が必要 | FD §3.2 維持、Member D 手戻りゼロ、観測性は Schedule 名 prefix で十分 |
| **Q5** | A | **A + SSM パス明示** | 軽微：`EUM_APPLICATION_ID` 注入経路の SSM パス命名が未定義 | パスを `/yudane/{env}{/init?}/cart/eum-application-id` に明示 |
| **Q6** | B（PlatformStack 共通 alertTopic） | **A'（CartStack 内 cartAlertTopic + 将来統合）** | 重大：PlatformStack に `alertTopic` 不在（grep で 0 hit）、Q6=B は「Unit-1 への破壊的拡張依頼」になり Member A 合意期限 5/29 18:00 に間に合わない可能性 | 本 Unit MVP デプロイブロッカー回避、将来 PlatformStack 整備後に subscription 追加で統合可能 |
| Q7 | A | A | 問題なし | — |
| Q8 | A | A | 問題なし | — |
| **Q9** | A（$15/月） | **A（$20-25/月）** | 軽微：APNs Sandbox / FCM dev token のコスト加算漏れ、5 sandbox の合算コストが過小評価 | 試算を $20-25/月 に更新、依然クレジット範囲内 |
| Q10 | A | A | 問題なし | — |

#### v2 → v3（4 件補強、選択肢自体は v2 のまま不変）

| Q | 補強内容 | 検出 Issue |
|---|---|---|
| **Q4** | AWS 公式 EventBridge Scheduler quotas（100 万 Schedule、Group 合算）の引用追加で Q4=A の仕様裏付け強化 | 軽微：v2 で AWS 仕様裏付け不足だった |
| **Q5** | APNs Production Cert + Apple Developer Program 登録（$99/年、決勝 2 週間前必須）を外部承認ブロッカーとして追記、backlog B-504 新規登録 | 軽微：Apple Developer Program 登録の前提条件が未明示 |
| **Q5** | `aws-mobiletargeting` 名前空間の将来移行リスク注記追加 | 軽微：CDK 名前空間置換可能性が未注記 |
| **Q6** | Slack Webhook 管理の SECURITY-08 引用誤り → SECURITY-01（KMS 暗号化）+ SECURITY-09（ハードニング）+ AGENTS.md §8 に修正 | 中：SECURITY-08 は IDOR / 重複処理防止であり外部 Webhook 管理と無関係、誤参照は読み手を混乱させる |

### Q1: Cross-Stack 依存解決の方式

PlatformStack / AuthStack / SafeguardStack の出力（KMS Key / DDB Table / Lambda ARN 等）を CartStack で参照する方式。

| 選択肢 | 内容 | メリット | デメリット |
|---|---|---|---|
| **A: CDK construct 直接参照（推奨）** | `props: { platformStack: PlatformStack, authStack: AuthStack, safeguardStack: SafeguardStack }` で TypeScript 型安全な参照 | 型補完 / リファクタ安全 / Functional Design §3.1 既定 | 1 つの `App` 内で全 Stack をインスタンス化する必要あり、Stack 単体テストが煩雑 |
| B: CFN Cross-Stack Reference | `Fn::ImportValue` で他 Stack の Output を参照 | Stack 単体デプロイが容易 | Output 削除に再デプロイ必須、命名衝突リスク |
| C: SSM Parameter 経由 | 全リソース ARN を SSM に登録、Lambda runtime で `ssm:GetParameter` | Stack 完全独立 / 動的解決可能 | ランタイム取得コスト（10ms/呼）、cold start 悪化、IAM ssm:GetParameter 追加必要 |

**推奨: A**（Functional Design §3.1 で既に `props.platformStack` / `props.authStack` / `props.safeguardStack` 前提で記述、Unit-1 構成と整合、変更すれば手戻り大）。

**[Answer]**: A

---

### Q2: 環境戦略（dev / staging / prd）

要件書 §6.1 / Unit-1 で `dev` と `prd` の 2 環境構成は既定。staging 環境の追加要否。

| 選択肢 | 内容 | コスト |
|---|---|---|
| **A: dev + prd の 2 環境（推奨）** | dev = 個人 sandbox（4 名）+ 共有 dev、prd = 決勝デモ用 1 環境のみ | $20-25/月 × prd（NFR §6.4.2）+ $3/月 × dev × 5 = $35-40/月 |
| B: dev + staging + prd の 3 環境 | staging = 統合テスト専用、決勝前リハーサル用 | + $20/月（staging 同等規模）= $55-60/月 |
| C: dev のみ + prd デモ直前作成 | コスト最小化 | 決勝直前 Stack 作成リスク、IT-09/IT-10 が dev でしか走らない |

**推奨: A**（ハッカソン期間 + クラウドクレジット範囲内、staging は backlog 化）。

**[Answer]**: A

---

### Q3: Lambda Layer 戦略

`shared/asin-extractor` / `shared/safeguard-policy` / `shared/telemetry-contracts` を 6 Lambda（cart_intake / cart_dismiss / cart_list / push_token / notification_dispatcher / cart_attack_scheduler_retry）にどう配布するか。

| 選択肢 | 内容 | コールドスタート影響 | 運用 |
|---|---|---|---|
| A: Lambda Layer に集約 | `yudane-shared-py-layer`（boto3 + pydantic + 3 shared lib） | Layer = 5MB、cold start +50-100ms | Layer バージョン管理が複雑 |
| **B: Lambda Function bundle に同梱（推奨）** | 各 Lambda の zip に shared を直接埋め込む（Poetry の path dependencies） | Layer なし、bundle = 4-6MB | Functional Design §6 / poetry path 依存と整合、Per-Unit deploy 単純化 |
| C: Container Image | ECR + コンテナイメージ Lambda | cold start +500-1000ms（SnapStart 効果消滅） | SnapStart の Q4=B' と矛盾、不採用一択 |

**推奨: B**（Unit-1 §6 で `poetry path dependencies` 確定済み、SnapStart の cold start 短縮効果を最大化）。

**[Answer]**: B

---

### Q4: EventBridge Scheduler の Group 戦略

One-time Schedule × 数千件作成における Group 構成。**v1 → v2 改訂**: 当初推奨 B（Group 2 分離）は FD §3.2 cdk-nag IAM Resource ARN `schedule/default/cart-*` と整合不一致を検出、A（default Group + Schedule 名 prefix）に格下げ。

| 選択肢 | 内容 | メリット | デメリット |
|---|---|---|---|
| **A: `default` Group のまま、Schedule 名 prefix で論理分離（推奨、改訂後）** | 攻撃ジョブ = `cart-attack-{userId}-{itemId}-{step}` / retry batch = `cart-retry-batch`（fixed name）で命名統一 | Functional Design §3.2 の cdk-nag suppression ARN（`schedule/default/cart-*`）と完全整合、Member D 手戻りゼロ、CloudWatch Metrics は Schedule 名で取得可能 | Group 単位の集計は不可（個別 Schedule 単位のみ） |
| B: `cart-attacks` 専用 Group + `cart-retry` 専用 Group の 2 つ | 攻撃ジョブと retry batch を Group 分離、観測性向上（Group 別 metrics）/ IAM scope 縮小 / 上限管理が独立 | **FD §3.2 の IAM Resource ARN を `schedule/cart-attacks/*` + `schedule/cart-retry/*` に書換必要、cdk-nag pass 期待が崩れる**、再検証コスト発生 |
| C: ユーザー別 Group | スケーラビリティ最大化 | 5K DAU で 5K Group 作成は管理コスト高、Group は静的リソース |

**推奨: A**（FD §3.2 整合維持、cdk-nag suppression を変更しない、観測性は Schedule 名 prefix で十分）。

**v3 改訂で追加（補強）**: AWS 公式 [EventBridge Scheduler quotas](https://docs.aws.amazon.com/scheduler/latest/UserGuide/scheduler-quotas.html) は **「アカウントあたり最大 100 万 Schedule」** と定義。**この上限は Group をいくつ作っても合算で適用される**ため、Group 分離（選択肢 B）はスケーラビリティ向上にならず、Group は単に「論理的なフォルダ分け」に過ぎない。本 Unit MVP 規模（数百件）/ 本番化規模（225 万件 → 月内に消化されるため同時保持は 75K 程度）どちらでも上限の 1/10 以下で十分余裕。Q4=A の根拠は**仕様裏付け面でも妥当**を確認。

**[Answer]**: A

---

### Q5: End User Messaging Push の Application 構成

旧 Pinpoint Application（≒ End User Messaging Application ID）を環境別にどう設定するか。

| 選択肢 | 内容 | 運用 |
|---|---|---|
| **A: dev / prd で別 Application（推奨）** | `yudane-cart-dev` / `yudane-cart-prd` を CDK で `aws-mobiletargeting` L1 で作成、SSM に Application ID を保存 | 環境分離明瞭、APNs Sandbox cert は dev のみ、prd は本番 cert |
| B: 単一 Application + dev/prd で別 Endpoint Tag | 共有 Application、Endpoint に `env=dev/prd` Tag | コスト微減、誤配信リスク（dev 端末に prd 通知） |
| C: 既存の Auth Stack の Application を流用 | Application を Auth Stack で 1 つ作成し全 Unit で共有 | Unit-2 owner との調整必要、Unit-2 Functional Design 確定前 |

**推奨: A**（環境分離を物理的に保証、APNs Sandbox / Production の cert 切替が単純化、Unit-2 owner 調整不要）。

**SSM Parameter パス命名（v2 改訂で追加、Issue 3 対応）**:

```
/yudane/{env}/cart/eum-application-id     # 共有 dev / prd
/yudane/dev/{init}/cart/eum-application-id # 個人 sandbox（C-4 Unit-1 整合）
```

B-06 NotificationDispatcher の Lambda 環境変数 `EUM_APPLICATION_ID` は CDK の `ssm.StringParameter.valueForStringParameter()` で deploy 時注入。動的 SSM 取得（`ssm:GetParameter` runtime 呼出）は採用しない（cold start 悪化回避）。

**v3 改訂で追加（Issue 6 / 7 対応）**:

#### APNs / FCM Certificate / Key の取得前提（外部承認ブロッカー）

| 項目 | dev | prd | 取得タイミング |
|---|---|---|---|
| **Apple Developer Program 登録**（$99/年） | 任意（個人 Apple ID + Sandbox push token で代替可） | **必須**（チームライセンスで Member D が登録、Member A 経費承認）| 決勝デモ（2026-06-26）の 2 週間前まで（cert 取得 + 配布 buffer 含む）|
| APNs Authentication Key（`.p8`） | Sandbox 用（Apple Developer 不要、Xcode 経由）| Production 用（Apple Developer Program 必須）| Apple Developer Program 登録 → Keys タブで生成（即時）|
| FCM Server Key | Firebase Console（無料、Google アカウントのみ）| 同左 | 即時取得可能 |

**ブロッカー判定**: Apple Developer Program 登録が決勝 2 週間前（2026-06-12）までに完了しない場合は backlog [B-503](../../../doc/backlog.md) Amazon Approved Mobile Application 申請と同列の外部承認ブロッカーとしてエスカレーション、決勝デモシナリオから Push 通知パートを縮退（dev cert で Sandbox 配信のみ表示する代替プラン）。**新規 backlog エントリ B-504 として登録**（必須 4 項目: 項目名 / 出典 / 後付けトリガー / 優先度）。

#### CDK 名前空間の将来移行リスク（注記）

End User Messaging は L2 construct がまだ未提供のため、`CfnApp`（`@aws-cdk/aws-mobiletargeting` 経由）の L1 で実装する。Unit-1 backlog [B-001](../../../doc/backlog.md) 観測性スタックとは独立。

> **将来リスク**: 旧 Pinpoint EoL 2026-10-30 に伴い、CDK の `aws-mobiletargeting` 名前空間自体は現状未廃止だが、将来的に `aws-end-user-messaging`（仮）等に置換される可能性あり（AWS 過去事例: `aws-applicationautoscaling` 等で名前空間移行履歴あり）。プロダクト化判断時に CDK 公式 changelog を確認し、移行が必要であれば backlog エントリ化する。本ハッカソン期間（〜2026-06-26）では現状の名前空間で問題なし。

**[Answer]**: A

---

### Q6: SNS Topic と Slack 配送の構成

5 系統の Alarms から Slack #yudane-emergency への配送経路。**v1 → v2 改訂**: 当初推奨 B（PlatformStack 共通 alertTopic）は再検証で **PlatformStack に `alertTopic` 不在**（grep で 0 hit）を検出、Unit-1 owner Member A への破壊的拡張依頼となり合意期限 5/29 18:00 に間に合わないリスクが高いため A'（CartStack 内 + 将来統合）に変更。

| 選択肢 | 内容 | メリット | デメリット |
|---|---|---|---|
| **A': CartStack 内に Cart 専用 SNS Topic + Slack Webhook、将来 Unit-1 alertTopic 整備後に subscription 追加（推奨、改訂後）** | `cartAlertTopic = new sns.Topic(this, 'CartAlertTopic')` + Slack Webhook を Stack 内で完結 | 本 Unit MVP デプロイブロッカー回避、Member A 合意プロセス不要、将来 PlatformStack に `alertTopic` が追加されたら `cartAlertTopic.addSubscription(...)` でリレー可能 | Slack Webhook が Unit 数だけ必要（決勝までに Unit-3/4/6/7/8 が同様に追加する場合は集約不可） |
| B: PlatformStack に共通 SNS Topic、各 Stack が SNS Subscribe | Slack Webhook 1 本、Alarm 集約閲覧、Unit-1 観測性スタック [B-001 backlog](../../../doc/backlog.md) と将来統合容易 | **PlatformStack に alertTopic が現状不在、Unit-1 への破壊的拡張依頼が必要、Member A 合意期限ブロッカーリスク** |
| C: 各 Alarm が Lambda → Slack 直接 | SNS 不要、コスト微減 | Lambda 5 個追加、運用オーバーヘッド大、リトライ複雑 |

**推奨: A'**（MVP デプロイブロッカー回避を最優先、将来統合可能性を残す）。

**Slack Webhook 値の管理**:

- AWS Secrets Manager に `yudane/cart/slack-webhook-url` として登録（dev / prd で別シークレット）
- CDK でシークレット参照、SNS Topic Subscription の `endpoint` に注入
- セキュリティ: **SECURITY-01（KMS 暗号化）+ SECURITY-09（ハードニング: デフォルト認証情報禁止）+ [AGENTS.md §8](../../../.kiro/steering/AGENTS.md)**（認証情報は AWS Secrets Manager / SSM 経由で管理）整合。コード・ドキュメント・コミット履歴に Webhook URL を直接記載しない

**将来統合の手順（PlatformStack 整備時）**:

1. Unit-1 owner Member A が PlatformStack に `alertTopic: sns.Topic` を追加（観測性スタック [B-001 backlog](../../../doc/backlog.md) の本実装時）
2. CartStack の `cartAlertTopic` に `addSubscription(new SnsSubscription(props.platformStack.alertTopic))` を追記
3. Slack Webhook サブスクリプションを Cart 側から外し、PlatformStack 側に移管
4. backlog エントリは削除せず「ステータス: 採用済み（YYYY-MM-DD）」を末尾追記

**[Answer]**: A'

---

### Q7: タグ戦略（コスト配分 + 運用）

リソース全体に付与する CDK Tag の最小集合。

| 選択肢 | 内容 |
|---|---|
| **A: 必須 4 タグ（推奨）** | `Environment` (dev/prd) / `Unit` (cart) / `Owner` (member-d) / `CostCenter` (yudane-hackathon-2026) |
| B: 8 タグ（A + ManagedBy / Stage / DataClassification / DemoFlag） | 監査性向上、cdk-nag のいくつか自動 pass | 過剰、運用コスト |
| C: 0 タグ（CDK デフォルトのみ） | 設定不要 | コスト追跡不能、prd デモ後の請求分析不能 |

**推奨: A**（AWS Cost Explorer で `Unit=cart` で本 Unit のコスト追跡可能、Owner で Member D の手戻り検知、CostCenter でハッカソン全体クレジット消費把握）。

**[Answer]**: A

---

### Q8: デプロイパイプライン拡張

Unit-1 で `.github/workflows/deploy-dev.yml` の `cdk-deploy-platform-dev` ジョブのみ存在。CartStack 用の拡張方針。

| 選択肢 | 内容 | 工数 |
|---|---|---|
| **A: deploy-dev.yml に `cdk-deploy-cart-dev` ジョブを追加（推奨）** | Member A が Unit-1 で確定したパターンを踏襲、PR merge → develop push → dev に自動 deploy | 0.5d、Unit-1 整合 |
| B: 個別 workflow ファイル作成（`deploy-cart-dev.yml`） | Cart 単独で deploy 制御可能 | 1d、Unit 数だけ workflow が増えて煩雑 |
| C: 手動デプロイのみ（CI 統合は決勝前） | Member D が `npm run deploy:dev:cart` を sandbox で実行 | 0d、CI/CD 評価軸の取りこぼし |

**推奨: A**（[Unit-1 §7.2](../../unit-1-platform/functional-design/functional-design.md) で「Unit-2 以降の Functional Design で順次追加」と既に予定、Member A との合意プロセス内で完結）。

**[Answer]**: A

---

### Q9: 個人 sandbox 環境の Lambda 実体作成方針

Unit-1 で `developerInitial` props 経由の sandbox 命名は確定済み。Member D の sandbox（`yudane-dev-d-cart-*`）で **Lambda 実体を作るか、共有 dev のものを参照するか**。**v1 → v2 改訂**: コスト試算を APNs Sandbox / FCM dev token 加算込みで再計算、$15/月 → $20-25/月。

| 選択肢 | 内容 | コスト（v2 修正後） | 開発体験 |
|---|---|---|---|
| **A: sandbox 内に Lambda 実体作成（推奨）** | DDB / Lambda / Scheduler / End User Messaging Application すべて sandbox 内で完結 | dev 共有 + 個人 sandbox × 4 = **$20-25/月**（APNs Sandbox token / FCM dev token / Schedule 短期生存込み） | 各メンバーが他者の影響受けず実装 |
| B: 共有 dev の Lambda を参照 + sandbox は DDB のみ | DDB は sandbox / Lambda は共有 | **$8-12/月**（DDB のみ sandbox） | 並行開発時に Lambda コード上書き衝突 |
| C: 共有 dev のみ、sandbox 不採用 | 全員が共有 dev に deploy | **$5-7/月** | Member D が Member B/C の作業中 deploy で破壊 |

**推奨: A**（並行開発 4 人を破壊的影響なく支える、月 $20-25 はクレジット範囲内、要件書 §6.6 並行性原則と整合）。

**コスト構成内訳（A 採用時、月額）**:

| 環境 | DDB | Lambda | Scheduler | End User Messaging | 小計 |
|---|---|---|---|---|---|
| 共有 dev | $1.5 | $1.0 | $0.0 | $0.5 | $3.0 |
| Member A sandbox | $0.5 | $0.5 | $0.0 | $0.5 | $1.5 |
| Member B sandbox | 同上 | 同上 | 同上 | 同上 | $1.5 |
| Member C sandbox | 同上 | 同上 | 同上 | 同上 | $1.5 |
| Member D sandbox | $1.5 | $1.0 | $0.0 | $1.5（実機テスト多） | $4.0 |
| prd | $1.5 | $1.0 | $0.0 | $0.5 | $3.0 |
| **合計** | — | — | — | — | **$14.5/月**（理論最小） |

実運用では Cold Start 効果検証 / 実機 Push 検証で **$20-25/月** に増加見込み。NFR Requirements §6.4.6 のクラウドクレジット枯渇時対応（80% 消費で sandbox 縮退）でカバー。

**[Answer]**: A

---

### Q10: ロールバック / 災害復旧戦略

prd 環境での Stack 更新失敗時の復旧手順。

| 選択肢 | 内容 |
|---|---|
| **A: CDK 自動ロールバック + DDB PITR（推奨）** | `cdk deploy --rollback` で CFN 自動復旧、DDB は PITR 35 日で時刻指定復元 |
| B: A + 手動スナップショット（1 日 1 回） | RPO 24h | DDB Backup スケジュール作成、月 +$2 |
| C: Multi-Region Active-Active | RPO 0 | 月 +$30、要件書 §6.1 リージョン `ap-northeast-1` のみ確定と矛盾、不採用 |

**推奨: A**（PITR は本 Stack で既に prd 有効、CFN Rollback も標準動作、ハッカソン規模で十分）。

**[Answer]**: A

---

## 4. 設問適用範囲チェック

[infrastructure-design.md](../../../.kiro/aws-aidlc-rule-details/construction/infrastructure-design.md) Step 3 の **MANDATORY** 7 カテゴリ評価:

| カテゴリ | 本 Plan での扱い | 設問 |
|---|---|---|
| Deployment Environment | dev/prd / 個人 sandbox | Q2 / Q9 |
| Compute Infrastructure | Lambda Layer / Reserved Concurrency / SnapStart 既定 | Q3（既定値レビュー含む） |
| Storage Infrastructure | DDB / EventBridge Scheduler / SSM | Q4 / Q5 / Functional Design 既定 |
| Messaging Infrastructure | EventBridge / End User Messaging / SQS DLQ / SNS | Q4 / Q5 / Q6 |
| Networking Infrastructure | API Gateway（Unit-1）/ VPC 外（Q5 Unit-1） | Functional Design 既定（VPC 外確定） |
| Monitoring Infrastructure | CloudWatch Alarms 5 系統 / SNS / Slack | Q6 / Functional Design §3.3 |
| Shared Infrastructure | PlatformStack 参照 / SNS 共有 / Layer 戦略 | Q1 / Q3 / Q6 |

**N/A**: なし（全 7 カテゴリで設問 or 既定値レビュー）。

---

## 5. Part 2 Generation で生成するファイル

Step 6 ルール準拠で以下 2 ファイルを生成:

1. `aidlc-docs/construction/unit-5-cart-intercept/infrastructure-design/infrastructure-design.md`
   - 物理マッピング表（論理 → AWS service → 環境別差異）
   - Stack の最終構成（Q1-Q10 反映後）
   - IAM Role / Policy 詳細（5 Lambda × 6 IAM = 30 statement の最小権限）
   - SSM Parameter 一覧
   - タグ戦略
   - cdk-nag suppressions 完全版

2. `aidlc-docs/construction/unit-5-cart-intercept/infrastructure-design/deployment-architecture.md`
   - デプロイ図（Mermaid）
   - デプロイ順序（Unit-1 Platform → Unit-2 Auth → **Unit-5 Cart** → Unit-7 Safeguard）
   - パイプライン CI/CD 仕様（GitHub Actions ジョブ拡張）
   - ロールバック / 災害復旧手順
   - 環境別差異表（dev / dev-sandbox / prd）

**Shared infrastructure 文書**: 本 v2 改訂（Q6 = A'）により PlatformStack への `alertTopic` 追加依頼は MVP では発生しないため、`aidlc-docs/construction/shared-infrastructure.md` の作成は不要。将来 Unit-1 観測性スタック [B-001 backlog](../../../doc/backlog.md) 本実装時に本 Unit から subscription を追加する旨のみ Plan §3 Q6 に記載済み。

---

## 6. 進捗チェックボックス

### Part 1 — Planning

- [x] Functional Design §3 / NFR Design 全文書を読み込み既確定事項を抽出
- [x] 7 カテゴリ評価で網羅性確認
- [x] Q1〜Q10 の推奨案 + 選択肢 + リスクを設計
- [x] [Answer]: タグ形式で配置
- [ ] ユーザー回答取得後 → ambiguity チェック → 必要なら follow-up
- [ ] Part 1 承認

### Part 2 — Generation（承認後）

- [x] `infrastructure-design.md` 生成（spec format 必須セクション 4 + 推奨 3 含む、Property 1/4/5/6 に Validates 参照付き）
- [x] `deployment-architecture.md` 生成（Mermaid + デプロイ順序 + CI/CD + 環境差異 + ロールバック + Smoke Test）
- [x] cart-stack.ts の Functional Design §3.1 への波及修正は v2 改訂で**ゼロ**（Q4=A / Q6=A' により FD §3.2 cdk-nag suppression 維持、PlatformStack 拡張依頼回避）
- [x] Member A への合意プロセス追加は v2 改訂で**不要**（Q6=A' により Slack Webhook を CartStack 内で完結）。ただし Q8=A の `deploy-dev.yml` 拡張依頼は新規発生のため deployment-architecture.md §6.1 で記録
- [x] B-504 backlog 登録（APNs Production Cert 取得、structure.md §6.1 必須 4 項目準拠）
- [x] 1 巡目セルフレビュー（Issue MMMM / NNNN / OOOO / PPPP の 4 件検出、MMMM / PPPP の 2 件修正、NNNN / OOOO は既存整合で skip）
- [x] aidlc-state.md / audit.md 更新
- [x] diagnostics エラーゼロ確認
- [ ] 完了通知 → 承認ゲート

---

## 7. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ステージの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: Cross-Stack 依存（Q1）/ デプロイ順序 / sandbox 戦略（Q9）で Unit-5 と他 Unit の責任分界が物理レベルで明示 |
| 創造性とテーマ適合性 | 維持: テーマ依存度は低いステージだが、3 段追撃の物理基盤を堅実に整備 |
| ドキュメント品質 | **強化**: 推奨案 + 選択肢 + リスクで Q1-Q10 を整理、評価者が物理判断の根拠を 1 文書で追跡可能 |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の Infrastructure Design を Functional / NFR と整合させた標準テンプレートで実施 |
