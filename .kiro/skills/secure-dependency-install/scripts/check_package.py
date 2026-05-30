#!/usr/bin/env python3
"""OSV.dev に照会してパッケージの既知脆弱性 (CVE) を深刻度付きで報告するスクリプト。

npm / PyPI の両エコシステムに対応。認証不要の OSV.dev 公開 API を利用する。

終了コード:
    0: 脆弱性なし、または Low のみ（インストール続行可）
    2: Medium の脆弱性あり（要ユーザー確認）
    3: High / Critical の脆弱性あり（インストールをブロック）
    1: 実行エラー（ネットワーク不通・引数不正など。offline.md にフォールバック）

使用例:
    python3 check_package.py --ecosystem npm --package lodash --version 4.17.20
    python3 check_package.py --ecosystem PyPI --package requests
    python3 check_package.py --ecosystem npm --package left-pad --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
NPM_REGISTRY = "https://registry.npmjs.org"
PYPI_JSON = "https://pypi.org/pypi"

# 終了コードの定義（呼び出し側はこれで分岐する）
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_MEDIUM = 2
EXIT_BLOCK = 3

# CVSS v3 スコア → 深刻度ラベルのしきい値
SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _http_get_json(url: str, timeout: int = 20) -> Any:
    """GET して JSON を返す。失敗時は例外を送出する。"""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, payload: dict, timeout: int = 20) -> Any:
    """JSON を POST して JSON を返す。失敗時は例外を送出する。"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_latest_version(ecosystem: str, package: str) -> Optional[str]:
    """バージョン未指定時に最新版を解決する。失敗したら None。"""
    try:
        if ecosystem == "npm":
            data = _http_get_json(f"{NPM_REGISTRY}/{package}")
            return data.get("dist-tags", {}).get("latest")
        if ecosystem == "PyPI":
            data = _http_get_json(f"{PYPI_JSON}/{package}/json")
            return data.get("info", {}).get("version")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError):
        return None
    return None


def cvss_score_to_label(score: float) -> str:
    """CVSS v3 スコアを深刻度ラベルに変換する。"""
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score > 0.0:
        return "LOW"
    return "NONE"


def _parse_cvss_vector(vector: str) -> Optional[float]:
    """CVSS v3 ベクタ文字列から base score を概算する。

    OSV は数値スコアを必ずしも持たないため、ベクタからの簡易計算をフォールバックに使う。
    厳密な公式実装ではないが、深刻度ラベル分類には十分な近似を返す。
    """
    try:
        metrics = dict(
            part.split(":", 1) for part in vector.split("/") if ":" in part
        )
    except ValueError:
        return None
    if "AV" not in metrics:
        return None

    av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}.get(metrics.get("AV", "N"), 0.85)
    ac = {"L": 0.77, "H": 0.44}.get(metrics.get("AC", "L"), 0.77)
    pr_map_unchanged = {"N": 0.85, "L": 0.62, "H": 0.27}
    pr_map_changed = {"N": 0.85, "L": 0.68, "H": 0.5}
    scope_changed = metrics.get("S", "U") == "C"
    pr = (pr_map_changed if scope_changed else pr_map_unchanged).get(
        metrics.get("PR", "N"), 0.85
    )
    ui = {"N": 0.85, "R": 0.62}.get(metrics.get("UI", "N"), 0.85)

    c = {"H": 0.56, "L": 0.22, "N": 0.0}.get(metrics.get("C", "N"), 0.0)
    i = {"H": 0.56, "L": 0.22, "N": 0.0}.get(metrics.get("I", "N"), 0.0)
    a = {"H": 0.56, "L": 0.22, "N": 0.0}.get(metrics.get("A", "N"), 0.0)

    iss = 1 - ((1 - c) * (1 - i) * (1 - a))
    if scope_changed:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
    else:
        impact = 6.42 * iss
    exploitability = 8.22 * av * ac * pr * ui

    if impact <= 0:
        return 0.0
    if scope_changed:
        base = min(1.08 * (impact + exploitability), 10)
    else:
        base = min(impact + exploitability, 10)
    # roundup to one decimal (ceil to nearest 0.1)
    return math.ceil(base * 10) / 10


def extract_severity(vuln: dict) -> tuple[str, Optional[float]]:
    """OSV の脆弱性レコードから (深刻度ラベル, スコア) を抽出する。"""
    best_score = -1.0
    # 1) severity フィールドの CVSS_V3 ベクタを優先
    for sev in vuln.get("severity", []) or []:
        score = _parse_cvss_vector(sev.get("score", ""))
        if score is not None and score > best_score:
            best_score = score
    # 2) database_specific.severity（GHSA 由来のラベル）をフォールバック
    if best_score < 0:
        label = (vuln.get("database_specific", {}) or {}).get("severity", "")
        label = str(label).upper()
        if label in SEVERITY_ORDER and label != "NONE":
            return label, None
    if best_score < 0:
        return "UNKNOWN", None
    return cvss_score_to_label(best_score), best_score


def extract_fixed_versions(vuln: dict, package: str) -> list[str]:
    """脆弱性が修正されたバージョンの一覧を抽出する。"""
    fixed: list[str] = []
    for affected in vuln.get("affected", []) or []:
        pkg = affected.get("package", {}) or {}
        if pkg.get("name") and pkg.get("name") != package:
            continue
        for rng in affected.get("ranges", []) or []:
            for event in rng.get("events", []) or []:
                if "fixed" in event:
                    fixed.append(event["fixed"])
    return sorted(set(fixed))


def query_osv(ecosystem: str, package: str, version: Optional[str]) -> list[dict]:
    """OSV.dev に照会して脆弱性レコードのリストを返す。"""
    pkg_obj: dict[str, str] = {"name": package, "ecosystem": ecosystem}
    payload: dict[str, Any] = {"package": pkg_obj}
    if version:
        payload["version"] = version
    result = _http_post_json(OSV_QUERY_URL, payload)
    return result.get("vulns", []) or []


def build_report(
    ecosystem: str, package: str, version: Optional[str], vulns: list[dict]
) -> dict:
    """判定用のレポート構造を組み立てる。"""
    findings = []
    highest = "NONE"
    for v in vulns:
        label, score = extract_severity(v)
        if label in SEVERITY_ORDER and SEVERITY_ORDER[label] > SEVERITY_ORDER.get(
            highest, 0
        ):
            highest = label
        findings.append(
            {
                "id": v.get("id"),
                "aliases": v.get("aliases", []),
                "summary": v.get("summary", ""),
                "severity": label,
                "cvss_score": score,
                "fixed_versions": extract_fixed_versions(v, package),
            }
        )
    decision = "ALLOW"
    if highest in ("CRITICAL", "HIGH"):
        decision = "BLOCK"
    elif highest == "MEDIUM":
        decision = "WARN"
    return {
        "ecosystem": ecosystem,
        "package": package,
        "version": version,
        "vulnerability_count": len(findings),
        "highest_severity": highest,
        "decision": decision,
        "findings": findings,
    }


def print_human(report: dict) -> None:
    """人間可読のサマリを出力する。"""
    pkg = f"{report['package']}@{report['version'] or 'latest'}"
    eco = report["ecosystem"]
    count = report["vulnerability_count"]
    if count == 0:
        print(f"✅ [{eco}] {pkg}: 既知の脆弱性は見つかりませんでした。")
        return
    icon = {"BLOCK": "🛑", "WARN": "⚠️", "ALLOW": "ℹ️"}.get(report["decision"], "ℹ️")
    print(
        f"{icon} [{eco}] {pkg}: {count} 件の脆弱性 / 最高深刻度 = "
        f"{report['highest_severity']} / 判定 = {report['decision']}"
    )
    for f in report["findings"]:
        ident = f["id"]
        aliases = ", ".join(f.get("aliases", []))
        ident_str = f"{ident} ({aliases})" if aliases else ident
        score = f["cvss_score"]
        score_str = f" CVSS {score}" if score is not None else ""
        print(f"  - [{f['severity']}{score_str}] {ident_str}")
        if f["summary"]:
            print(f"      {f['summary']}")
        if f["fixed_versions"]:
            print(f"      修正版: {', '.join(f['fixed_versions'])}")
        else:
            print("      修正版: なし（代替パッケージ検討 or 導入見送りを推奨）")


def decision_to_exit_code(decision: str) -> int:
    return {"BLOCK": EXIT_BLOCK, "WARN": EXIT_MEDIUM, "ALLOW": EXIT_OK}.get(
        decision, EXIT_OK
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OSV.dev に照会してパッケージの既知脆弱性を深刻度付きで報告する"
    )
    parser.add_argument(
        "--ecosystem",
        required=True,
        choices=["npm", "PyPI"],
        help="対象エコシステム（npm または PyPI）",
    )
    parser.add_argument("--package", required=True, help="パッケージ名")
    parser.add_argument(
        "--version",
        default=None,
        help="バージョン（省略時は最新版を解決して照会）",
    )
    parser.add_argument(
        "--json", action="store_true", help="機械可読な JSON で出力する"
    )
    args = parser.parse_args()

    version = args.version
    if not version:
        resolved = resolve_latest_version(args.ecosystem, args.package)
        if resolved:
            version = resolved

    try:
        vulns = query_osv(args.ecosystem, args.package, version)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as exc:
        msg = (
            f"OSV.dev への照会に失敗しました: {exc}. "
            "references/offline.md の CLI 手順にフォールバックしてください。"
        )
        if args.json:
            print(json.dumps({"error": str(exc), "decision": "ERROR"}, ensure_ascii=False))
        else:
            print(f"❌ {msg}", file=sys.stderr)
        return EXIT_ERROR

    report = build_report(args.ecosystem, args.package, version, vulns)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    return decision_to_exit_code(report["decision"])


if __name__ == "__main__":
    sys.exit(main())
