---
inclusion: always
---

# ハッカソン評価基準（コア）

> このファイルは常にコンテキストに含まれます。すべての成果物・応答・意思決定はここに示す 4 基準とテーマを念頭に置いて行うこと。
>
> 詳細なチェックリスト・スケジュール・各ステージ指示は [hackathon-stage-checklists.md](./hackathon-stage-checklists.md)（fileMatch steering、`aidlc-docs/**` 編集時に自動発火）を参照。

---

## 🏆 イベントとテーマ

- **イベント**: AWS Summit Japan 2026 AI-DLC ハッカソン
- **テーマ**: 「人をダメにするサービスを考えよう！」
  - サービス自体に AI 必須ではない。**「人をダメにできるアイデアそのもの」** が評価対象
- **現在のフォーカス**: 書類審査（Inception フェーズ成果物、締切 **2026-05-10（日）23:59**）

その他のスケジュールは [hackathon-stage-checklists.md](./hackathon-stage-checklists.md) §スケジュール を参照。

---

## 📋 4 審査基準（書類審査）

1. **ビジネス意図（Intent）の明確さ** — 「誰を・どうダメにするのか」が一文で説明でき、物語的根拠がある
2. **Unit 分解の適切さ** — 並行開発可能な Unit of Work に分解され、依存関係が明示されている
3. **創造性とテーマ適合性** — 便利の先の「退化」に踏み込み、世界観・中核メカニクスが設計に入っている
4. **ドキュメントの品質** — README で 5 秒で刺さり、`aidlc-docs/` 配下の成果物が揃い、Markdown / Mermaid が崩れない

予選・決勝の評価軸は別レイヤ（MVP 完成度・AI-DLC プロセス・プレゼン）。詳細は [hackathon-stage-checklists.md](./hackathon-stage-checklists.md) §3 段階の審査 を参照。

---

## 🎯 意思決定時に常に自問する 3 点

各ステージ完了・重要判断時に必ずセルフチェック:

1. この成果物は書類審査の 4 基準のどれに貢献したか？
2. テーマ「人をダメにする」を引き続き体現できているか？
3. 次のステージに進むことで、評価点を取りこぼすリスクはないか？

回答は `aidlc-docs/aidlc-state.md` の Stage Progress に反映する。

---

## 🚫 避けるべきアンチパターン

- ❌ テーマが曖昧で「結局ただの便利ツール」になっている
- ❌ 単一 Unit で済ませてしまい Unit 分解の評価を取り逃がす
- ❌ README が雑で `aidlc-docs/` 配下を見ないと全体像が掴めない
- ❌ AI 活用が目的化し、**テーマ適合性が薄い**
- ❌ ネタに寄りすぎて実装可能性ゼロ、or 真面目すぎてユーモアがない
- ❌ 公序良俗や倫理的配慮を欠いたアイデア（違法・差別・健康被害を実害として引き起こすもの）

---

## 💡 判断の基本姿勢

- **テーマ適合性の維持**: どのステージでも「人をダメにする」軸を忘れず、成果物に反映する
- **ドキュメントファースト**: 書類審査の提出物はドキュメントそのもの。コードより先にドキュメント品質を担保する
- **Adaptive Workflow の効果最大化**: スキップ判断はハッカソン評価との整合性を優先。Units Generation / Application Design は「Unit 分解の適切さ」のため原則 EXECUTE
- **日本語対話**: ユーザーが日本語で対話している限り、質問ファイル・応答・ドキュメントは日本語（技術用語の英語併記 OK）

各ステージでの詳細な遵守事項・書類審査チェックリスト・スケジュールは [hackathon-stage-checklists.md](./hackathon-stage-checklists.md)（fileMatch、`aidlc-docs/**` 編集時に自動発火）を参照。

---

## 🔗 参照リンク

- [ハッカソン公式ページ](https://pages.awscloud.com/summit-japan-2026-hackathon-reg.html)
- [AI-DLC 解説ブログ](https://aws.amazon.com/jp/blogs/news/ai-driven-development-life-cycle/)
- [aidlc-workflows GitHub](https://github.com/awslabs/aidlc-workflows)
