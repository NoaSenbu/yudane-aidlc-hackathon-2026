# Unit-1 Platform — Infrastructure Design Clarification

> Infrastructure Design の Q7 について、確定済み設計との矛盾を確認する。
> 確定済み: Q1=A / Q2=A / Q3=A / Q4=A / Q5=A（「___a」を A と解釈）/ Q6=A
> 作成: 2026-05-29

---

## 確認 1: Q5 の記入

**あなたの回答**: Q5=「___a」

→ `a` が明示されているため **A**（MVP は基盤 + 主要アラート、決勝でフル）と解釈しました。これで問題なければ Clarification 1 のみ回答してください。違う場合は下記 Clarification 0 に記入してください。

### Clarification Question 0（任意）
Q5 の意図は A で正しいですか？

A) はい、A（MVP は基盤 + 主要アラート、決勝でフル）で正しい
B) いいえ（[Answer]: の後に正しい選択肢を記述）

[Answer]: A

---

## 矛盾 1: ElastiCache / OpenSearch の配置（元 Q7=C）

**あなたの回答**: Q7=C「両方とも利用 Unit（Unit-4/5）のスタックに委譲し platform-stack に含めない」

**検出された矛盾**:

| # | 矛盾先 | 内容 |
|---|---|---|
| 1 | unit-of-work.md Unit-1 範囲 | Unit-1 Infra 範囲に「ElastiCache Redis / OpenSearch Serverless」が明示的に含まれる。C はこの範囲定義の変更を伴う |
| 2 | 共有リソースのクロススタック依存 | ElastiCache Redis は B-11 CreatorsApiClient（商品メタ TTL 6h）+ レート制限 + セッションで使われ、**Unit-4 Reel と Unit-5 Cart の両方**が依存。片方の Unit スタックに置くと他方が Export/Import 依存になり tech-cdk.md §3（Export/Import 回避）と不整合 |

**補足**: OpenSearch Serverless は実質 Unit-4 Reel 専用のため、これだけ Unit-4 へ委譲するのは合理的。問題は「共有される ElastiCache」をどこに置くか。

### Clarification Question 1
ElastiCache Redis と OpenSearch Serverless の配置をどうしますか？

A) **元の A（段階構築、推奨）**: 両方とも platform-stack に配置。ElastiCache は MVP で最小ノード構築（Unit-4/5 が共有）、OpenSearch は Unit-4 着手時に platform-stack へ追加（MVP は小規模コレクション）。共有リソースを基盤に集約しクロススタック依存を回避
B) **ハイブリッド**: 共有される ElastiCache Redis は platform-stack に配置（Unit-4/5 が共有）、Unit-4 専用の OpenSearch Serverless のみ reel-stack（Unit-4）に委譲。責務に応じて分離
C) **元の C を維持**: 両方とも利用 Unit のスタックに委譲（→ unit-of-work.md の Unit-1 範囲改訂 + ElastiCache の所有 Unit 決定 + クロススタック参照方法（SSM 経由）の設計が別途必要。影響中）
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## 補足: 各選択肢の影響

- **A（推奨）**: unit-of-work.md と完全整合。共有リソースを基盤に集約し、各 Unit は SSM 経由で接続情報を参照するだけで済む（疎結合）
- **B**: 「Unit-4 専用は Unit-4 が持つ」という責務分離は綺麗。ただし OpenSearch は Unit-1 着手時点では作らず Unit-4 着手時に reel-stack で作る形になり、platform-stack の VPC/Subnet を Unit-4 が参照する（SSM 経由）
- **C**: ElastiCache の所有 Unit を決める必要があり、共有のため必ずどこかでクロススタック依存が発生。unit-of-work.md の改訂も伴うため影響が中程度
