# Unit-2 Auth & Profile — NFR Requirements Clarification

> Unit-2 NFR Requirements の Q2 / Q3 について、矛盾・不整合を確認する。
> 確定済み: Q1=C / Q4=A
> 作成: 2026-05-29

---

## 矛盾 1: オンボ完了率の計測（Q2=C vs Q5=B）

**あなたの回答**: Q2=C「オンボ完了率を MVP で計測しない」かつ Q5=B「サインイン成功率 + **オンボ完了率** を計測する」

**矛盾**: Q5=B は完了率を計測対象に含めているが、Q2=C は計測しないとしている。両者は両立しない。

### Clarification Question 1
オンボーディング完了率の MVP 計測をどうしますか？

A) **計測する（Q2=A 相当 + Q5=B のメトリクス）**: サインイン成功率 + オンボ完了率を EMF で計測（Unit-1 土台）。画面別離脱は決勝で追加。ダメ化ファネルの起点として MVP から押さえる
B) **計測しない（Q2=C + Q5 もオンボ完了率を外す）**: MVP はメトリクスを最小化し、サインイン成功率のみ。完了率含む全計測は決勝
X) Other（[Answer]: の後に記述）

[Answer]: B

---

## 不整合 2: MFA 周辺機能と Functional Design の AC（Q3=C）

**あなたの回答**: Q3=C「MVP は MFA 基本のみ、ロックアウト/リセット冷却は決勝」

**不整合**: 承認済みの Unit-2 Functional Design で以下が**受入条件として確定済み**:
- US-AUTH-02 AC-3: MFA リセットは 72h 冷却後
- US-AUTH-02 AC-4: 認証失敗 5 回で 15 分ロックアウト
- US-AUTH-03: 負債セーフガード（初回冷却 + 72h クーリングオフ）

Q3=C にするとこれらが MVP で未実装になり、予選 5/30 の「動作する MVP」評価で US-AUTH-02/03 が未達ストーリーになる。

**切り分け**: ロックアウト・リセット冷却の「ロジック」は MVP に必要だが、「CloudWatch Alarm の作り込み・異常検知・監査ログ 90 日保持」は決勝に回せる。

### Clarification Question 2
MFA / 認証の MVP スコープをどうしますか？

A) **Q3=A 相当（推奨）**: MVP = MFA 必須 + 5 回失敗 15 分ロック + 72h リセット冷却（= FD の AC を満たす）。決勝 = CloudWatch Alarm 完備 + 異常検知 + 監査ログ 90 日。AC 未達を避けつつ Alarm 作り込みは決勝
B) **Q3=C のまま進める**: MVP は MFA 基本のみ。ただし US-AUTH-02 AC-3/AC-4 と US-AUTH-03 を MVP スコープ外として Functional Design を改訂し、ストーリーのデモ範囲を縮小（要件・stories の更新を伴う）
X) Other（[Answer]: の後に記述）

[Answer]: B

---

## 補足
- **Clarification 1=A / 2=A** を選ぶと、Unit-1 の段階達成方針（Q7=A）と完全整合し、FD の AC をすべて MVP で満たす。Alarm の作り込みなど純粋な「運用の磨き込み」のみ決勝に回る
- **B 系**を選ぶ場合、MVP の負荷は下がるが、予選で見せられる Unit-2 の価値（安全なオンボ + MFA）が縮小し、FD/stories の改訂が必要


---

## 最終確認 3: US-AUTH-03（負債セーフガード）の MVP スコープ（Clarification 2=B を受けて）

**状況**: Clarification 2=B で「US-AUTH-02 AC-3/AC-4 + US-AUTH-03 を MVP スコープ外」と回答。MFA の Alarm 作り込み決勝送りは受理。ただし US-AUTH-03 のみ再考を依頼。

**新情報（再考の根拠）**:
- US-AUTH-03 の中核は Unit-1 `SafeguardPolicy.decideAllow`（DEBT 比率 0.35）の**呼び出しのみ**。MVP 追加コストはほぼゼロ
- US-AUTH-03 は NG-4（金融実害）への配慮の実装本体。README / ng-scenarios.md で倫理ラインとして明文化済み
- MVP から外すと予選デモが「借金保有者に上限半減・冷却なしで散財させる」状態になり、ハッカソン評価のアンチパターン（倫理配慮欠如）に抵触

### Clarification Question 3
US-AUTH-03（負債セーフガード）の MVP スコープをどうしますか？

A) **US-AUTH-03 は MVP に残す（推奨）**: 負債フラグ保存 + Unit-1 SafeguardPolicy 連携（上限半減・初回冷却）+ 72h クーリングオフは MVP で実装。MFA の Alarm 作り込み・異常検知・監査ログ 90 日のみ決勝送り（= Clarification 2 のうち MFA 運用部分だけ B、US-AUTH-03 は A）
B) **US-AUTH-03 も MVP スコープ外（元の 2=B 通り）**: 倫理リスクを承知の上で決勝送り。FD/stories/README の倫理記述を「決勝で実装」と注記する改訂を伴う
X) Other（[Answer]: の後に記述）

[Answer]: 
