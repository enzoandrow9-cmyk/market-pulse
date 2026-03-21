from __future__ import annotations


def build_markdown_report(result: dict) -> str:
    perf = result.get("performance_metrics", {})
    risk = result.get("risk_metrics", {})
    trade = result.get("trade_statistics", {})
    lines = [
        "# Quant Lab Research Report",
        "",
        f"- Total return: {perf.get('total_return', 0.0):.2%}",
        f"- Annualized return: {perf.get('annualized_return', 0.0):.2%}",
        f"- Sharpe ratio: {perf.get('sharpe_ratio', 0.0):.2f}",
        f"- Max drawdown: {risk.get('max_drawdown', 0.0):.2%}",
        f"- Trade count: {trade.get('trade_count', 0)}",
        "",
        f"Regime: {result.get('regime', {}).get('regime', 'unknown')}",
        f"Experiment: {result.get('experiment', {}).get('experiment_id', 'n/a')}",
    ]
    return "\n".join(lines)
