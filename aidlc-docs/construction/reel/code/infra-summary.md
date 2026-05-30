# Unit-4 Reel — Code Summary: Infra（Step 9）

> `infra/lib/reel-stack.ts` の生成サマリ。Snapshot TDD（CDK assertions + cdk-nag）。
> 確定方針: Infra Q1〜Q7=A + 横断矛盾解消反映済み

## 生成物

| ファイル | 役割 |
|---|---|
| `infra/lib/reel-stack.ts` | reel-stack（DynamoDB 2 / feed・transition Lambda / API パス / usage plan 429 / SSM / Alarm） |
| `infra/test/reel-stack.test.ts` | CDK assertions（テーブル/Lambda/Alias/SSM/UsagePlan）+ cdk-nag 未抑制エラー 0 |
| `infra/bin/app.ts`（更新） | reel-stack を env 切替で登録（platform 後段） |

## reel-stack の構成（MVP）

- **DynamoDB**: `amazon-transitions`（PK=userId / SK=transitionId、gsi-month、On-Demand/PITR/SSE-KMS/TTL）+ `impressions`（PK=userId / SK=shownAtCardId）
- **Lambda**（VPC 外、Python 3.13 + ARM64 + SnapStart + live Alias）: `reel-feed`（B-03 + B-10 同梱）/ `reel-transition`（B-13 + B-10 同梱）
- **API**: platform の単一 API を `RestApi.fromRestApiAttributes()` で import し `/v1/reel`(GET) / `/v1/amazon-transitions`(POST) を追加。usage plan で 429（SECURITY-11）
- **共有資源継承**: KMS / SNS を SSM 参照（`valueForStringParameter`、Export/Import 不使用）
- **SSM 公開**: `bedrock-model-id` / `creators-approved`（feature フラグ）/ `transitions-table-name`
- **Alarm**: feed/transition のエラー率 → platform SNS
- **IAM**: テーブル単位の grant（最小権限）、cdk-nag suppression に理由コメント

## MVP / 決勝の差（feature フラグ）
- MVP: VPC なし・Redis なし・OpenSearch なし・catalog Lambda なし（ダミーカタログはアプリ同梱）
- 決勝: `creators-approved=true` 時に VPC 内 catalog Lambda（B-11）+ Redis + OpenSearch を追加（本スタックに後続 PR で拡張）

## ⚠️ Unit-1 への依頼事項（cross-unit 依存、要 Member A 対応）
reel-stack は以下の SSM パラメータを参照するが、**現状 platform-stack は未公開**:
- `/yudane/<env>/platform/api-id`
- `/yudane/<env>/platform/api-root-resource-id`

platform-stack は現在 `vpc-id` / `private-subnet-ids` / `userpool-id` / `userpool-client-id` / `redis-endpoint` / `kms-key-arn` / `alerts-topic-arn` / `lambda-sg-id` を公開しているが、**API Gateway の id / root-resource-id を公開していない**。reel（および debate/cart）が API にパス相乗りするには Unit-1 がこの 2 パラメータを公開する必要がある。
→ **Member A（Unit-1）へ API Gateway 構築 + api-id/root-resource-id の SSM 公開を依頼**（決勝の統合前提）。OpenSearch コレクション追加も同様に Unit-4 着手として依頼済み（infrastructure-design.md §1）。

## 検証メモ
- 全 infra ファイル diagnostics 0
- **cdk synth / snapshot test 実行は Build and Test 段**（node_modules 未セットアップ）。CI `ci.yml` の infra ジョブで実行
- Lambda コードは `fromInline` プレースホルダ（バンドルは Build and Test で `backend/src/reel` を結線）
