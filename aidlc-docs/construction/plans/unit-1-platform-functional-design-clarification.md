# Unit-1 Platform — Functional Design Clarification

> Functional Design Plan の Q1 / Q4 について、ユーザー指摘を受けて方向性を確定するための追加質問。
> 確定済み: Q2=A / Q3=A / Q5=A / Q6=A / Q7=A
> 作成: 2026-05-29

---

## Clarification 1: OpenAPI 第1版の凍結範囲（元 Q1）

**ユーザー指摘**: 実装者によってパス定義は変わるので、パスを実装した人が OpenAPI に追記していく方が良いのではないか。

**AI 分析（要約）**: 全面 incremental 方式は (1) Prism モックによる並行開発の前提が崩れる、(2) Unit-1 の成功条件「OpenAPI 凍結」を満たせない、(3) 共通規約の整合レビューが効かない、(4) 型生成 PR が頻発しコンフリクト増、という問題がある。一方で「第1版で全フィールド確定」は過剰。両者の中間（骨格は凍結、詳細フィールドは非破壊で実装者が追記）が最適。

### Clarification Question 1
OpenAPI 3.1 第1版の凍結範囲をどうしますか？

A) **Refined A（ハイブリッド、推奨）**: 第1版では「全 UC のパス骨格（URL・メソッド）+ 共通コンポーネント（ProblemDetails / 認証 / ページネーション / 共通パラメータ）+ 主要リソースの必須フィールド最小セット」を Member A が凍結。各実装者は担当パスの**省略可能フィールドを後から非破壊的に追記**（契約 PR → 型再生成 → 実装 PR の順序を厳守）。骨格凍結で並行開発を担保しつつ、詳細は実装者が育てる
B) 元の A（第1版で全 UC のエンドポイント + 主要フィールドまで Member A が一括定義し凍結。実装者の追記は最小限）
C) 全面 incremental（共通コンポーネントのみ第1版で凍結。パスは各実装者が実装時に随時追記）— ユーザー原案に近い
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## Clarification 2: PII マスキングの fail-safe 化（元 Q4）

**ユーザー指摘**: 鍵名ベースのマスキング（A）だと、PII にあたるカラムが増えたときにマスクルールを適用し忘れるとログに出てしまうのではないか。

**AI 分析（要約）**: 指摘は正しい。鍵名 denylist は fail-open（登録漏れ = 漏洩）。SECURITY 全面適用方針では default-deny（ホワイトリスト）に反転し、「許可リストに足し忘れたらマスクされる（安全側）」とすべき。

### Clarification Question 2
B-12 AuditLogger / S-04 TelemetryContracts の PII 保護方式をどうしますか？

A) **Refined A（default-deny、fail-safe、推奨）**: ログ・テレメトリに出力してよいフィールドを S-04 TelemetryContracts で**ホワイトリスト化**し、未登録キーはデフォルトでマスク。さらに OpenAPI フィールドに `x-pii: true` を付与した項目はログ経路で必ずマスク。CI（check-pii-fields 拡張）で未分類フィールドを検出したら fail。新カラム追加時は安全側（マスク）に倒れる
B) ハイブリッド: 既知の PII は鍵名 denylist で自動マスク（元 A）+ ログに渡す構造体は許可リスト外を warn ログに記録（マスクはするが denylist が主、ホワイトリストは検知補助）
C) 元の A のまま（鍵名 denylist のみ。運用ルールで新規 PII 追加時のマスクルール追記を徹底）
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## 補足: 性能・実装コストへの影響

- **Clarification 1**: refined A は B/C と比べて Member A の初期作業がやや増える（全パス骨格の設計）が、Unit-1 の工数目安 2〜3 日に収まる範囲。並行開発の立ち上がりが最速になる
- **Clarification 2**: refined A はホワイトリスト維持の手間が増えるが、漏洩リスクを構造的に排除できる。ハッカソンの SECURITY 全面適用要件（SECURITY-09 等）に最も整合
