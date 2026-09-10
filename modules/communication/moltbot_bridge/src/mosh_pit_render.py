"""Deterministic, script-free HTML for already authorized Mosh Pit projections.

Rendering is not authentication. Hosts must call project_mosh_pit through a
trusted authorized source before using this renderer on any private data.
"""

from html import escape
from typing import Any, Mapping


TRUTH_LABELS = {
    "OBSERVED": "記録あり",
    "REPORTED_BY_012": "012からの報告",
    "INFERRED": "推定",
    "PROPOSED": "提案",
}


def render_mosh_pit_html(projection: Mapping[str, Any]) -> str:
    """An embeddable fragment: date headings, activity bullets, folded threads."""
    def text(value: Any) -> str:
        return escape(str(value), quote=True)

    def details(entry: Mapping[str, Any]) -> str:
        label = TRUTH_LABELS[entry["truth"]]
        return '<small>' + label + '</small>' + ''.join(
            '<p>' + text(line) + '</p>' for line in entry["details"]
        )

    parts = ['<section class="mosh-pit" aria-label="活動ログ">']
    for day in projection["days"]:
        parts.append('<h2>' + text(day["date"] or "日付未確認") + '</h2><ul>')
        for entry in day["entries"]:
            parts.append('<li><details><summary>' + text(entry["actor"]) + '：' + text(entry["summary"]) + '</summary>')
            parts.append(details(entry))
            if entry["replies"]:
                parts.append('<ol aria-label="この活動についてのやり取り">')
                for reply in entry["replies"]:
                    parts.append('<li><p>' + text(reply["actor"]) + '：' + text(reply["summary"]) + '</p>' + details(reply) + '</li>')
                parts.append('</ol>')
            if entry["more_replies"]:
                parts.append('<p>続きのやり取りがあります。</p>')
            parts.append('</details></li>')
        parts.append('</ul>')
    if not projection["days"]:
        parts.append('<p>表示できる活動はまだありません。</p>')
    if projection["has_more"]:
        parts.append('<p>以前の活動があります。</p>')
    parts.append('</section>')
    return ''.join(parts)
