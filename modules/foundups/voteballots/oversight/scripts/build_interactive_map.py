"""Render the public Oversight maps from reviewed static records."""

from html import escape
import json
import re
from urllib.parse import urlsplit


MAP_FILES = ("map-core.json", "map-authority.json", "map-investigation.json", "map-legal.json")
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
DIAGRAM = (
    ("overview",),
    (("overview", "house", "House authority"), ("overview", "senate", "Senate authority")),
    ("house", "senate"),
    (("house", "review", "House approvals"), ("senate", "review", "Senate approvals")),
    ("review",),
    (("review", "follow-money", "Records"), ("review", "test-evidence", "Review"), ("review", "witnesses", "Witnesses")),
    ("follow-money", "test-evidence", "witnesses"),
    (("follow-money", "decisions", "Provenance"), ("test-evidence", "decisions", "Findings"), ("witnesses", "decisions", "Restrictions")),
    ("decisions",),
    (("decisions", "congressional-action", "Committee approval"), ("decisions", "coordination", "Separate state authority")),
    ("congressional-action", "coordination"),
)
DIAGRAM_GATES = {
    ("overview", "house"): "Identify the legislative purpose, committee with jurisdiction and authority under House rules before a formal inquiry.",
    ("overview", "senate"): "Identify the legislative purpose, committee with jurisdiction and authority under Senate rules before a formal inquiry.",
    ("house", "review"): "House committee officials approve the collection methods and the handling of evidence under their own rules. Shared review requires defined access and disclosure permissions.",
    ("senate", "review"): "Senate committee officials approve the collection methods and the handling of evidence under their own rules. A House decision supplies no Senate approval.",
    ("review", "follow-money"): "Identify the records that could answer the question, confirm lawful access, and record custody and limits before tracing transfers.",
    ("review", "test-evidence"): "Record exact sources and separately review gaps, contradictions, alternative explanations and proposed findings.",
    ("review", "witnesses"): "Check who can contact the witness and how statements and restrictions will be recorded. Cooperation, immunity and clemency have separate authorities.",
    ("follow-money", "decisions"): "Advance only the transfer links the records support. Preserve the counterevidence, limits and open questions.",
    ("test-evidence", "decisions"): "A reviewer checks the findings and counsel screens the proposed action and any disclosure.",
    ("witnesses", "decisions"): "Respect use and disclosure restrictions. Any prosecutor relying on independent sources must document that provenance.",
}
ENTRY_LABELS = {
    "authority": "Explore the structure",
    "investigation": "Walk through an investigation",
    "lessons": "Lessons and failure points",
}


def link_is_safe(href: str) -> bool:
    if re.fullmatch(r"/[a-zA-Z0-9_./#-]*", href) and not href.startswith("//"):
        return ".." not in href.split("#", 1)[0].split("/")
    url = urlsplit(href)
    return bool(url.scheme == "https" and url.hostname and not (url.username or url.password)
                and not re.search(r"[\s\\]", href))


def breadcrumbs(nodes, key):
    path = []
    while key is not None:
        if key not in nodes or key in path:
            raise ValueError(f"Invalid map parent chain at {key}")
        path.append(key)
        key = nodes[key]["parent"]
    if path[-1] != "overview":
        raise ValueError("Map paths must end at Oversight")
    return list(reversed(path))


def load_map(read_source):
    nodes = {}
    for name in MAP_FILES:
        for key, value in json.loads(read_source(name)).items():
            if not ID.fullmatch(key) or key.startswith("edge-") or key in nodes:
                raise ValueError(f"Invalid or duplicate map node {key}")
            nodes[key] = value
    for key, node in nodes.items():
        if not node["title"].strip() or not node["summary"].strip():
            raise ValueError(f"Missing title or summary on {key}")
        breadcrumbs(nodes, key)
        targets = set()
        for target, gate in node.get("choices", []):
            if target not in nodes or target == key or target in targets or not gate.strip():
                raise ValueError(f"Invalid map connection {key} to {target}")
            targets.add(target)
        for target, evidence in node.get("connection_evidence", {}).items():
            if target not in targets or not node.get("fictional") or not evidence:
                raise ValueError(f"Invalid fictional connection evidence on {key} to {target}")
            if any(not label.strip() or not text.strip() for label, text in evidence):
                raise ValueError(f"Empty fictional evidence on {key} to {target}")
        for label, href in node.get("links", []):
            if not label.strip() or not link_is_safe(href):
                raise ValueError(f"Invalid map source link on {key}")
    for (origin, target), gate in DIAGRAM_GATES.items():
        choices = nodes[origin].setdefault("choices", [])
        if target not in dict(choices):
            choices.append([target, gate])
    if "decisions" not in dict(nodes["authority"]["choices"]):
        nodes["authority"]["choices"].append(["decisions", "Use the reviewed record to identify which authorized outcomes are available."])
    reachable = {"overview"}
    pending = ["overview"]
    while pending:
        for target, _ in nodes[pending.pop()].get("choices", []):
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    if unreachable := set(nodes) - reachable:
        raise ValueError(f"Unreachable map nodes: {sorted(unreachable)}")
    return nodes


def edge_id(origin, target):
    return f"edge-{origin}--{target}"


def diagram(nodes, prefix=""):
    rows = []
    for row in DIAGRAM:
        items = []
        for item in row:
            if isinstance(item, tuple):
                origin, target, label = item
                if target not in dict(nodes[origin]["choices"]):
                    raise ValueError(f"Missing diagram connection {origin} to {target}")
                classes = "map-wire conditional" if target == "coordination" else "map-wire"
                description = f"{label}: {nodes[origin]['title']} to {nodes[target]['title']}"
                items.append(f'<a class="{classes}" href="{prefix}#{edge_id(origin, target)}" aria-label="{escape(description)}">{escape(label)}</a>')
            else:
                label = "Independent state action" if item == "coordination" else nodes[item]["title"]
                items.append(f'<a class="map-box map-box-{item}" href="{prefix}#{item}">{escape(label)}</a>')
        rows.append(f'<div class="map-row map-row-{len(row)}">{"".join(items)}</div>')
    return '<nav class="map-diagram" aria-label="Interactive oversight diagram">' + "".join(rows) + "</nav>"


def entry_links(prefix=""):
    items = []
    for key, label in ENTRY_LABELS.items():
        style = "primary" if key == "authority" else "outline"
        items.append(f'<a class="button {style}" href="{prefix}#{key}">{label}</a>')
    return '<div class="actions">' + "".join(items) + "</div>"


def choice_cards(nodes, key, targets, labels=None):
    rows = []
    for target in targets:
        label = escape(labels[target] if labels else nodes[target]["title"])
        rows.append(f'<li><a class="map-wire" href="#{edge_id(key, target)}" aria-label="Why this connection? {label}">Why this connection?</a><a class="map-box" href="#{target}">{label}</a></li>')
    return f'<ul class="map-choices">{"".join(rows)}</ul>'


def map_screen(nodes, key, title, summary, path, body="", *, fictional=False):
    parent = path[-2] if key == path[-1] and len(path) > 1 else path[-1]
    trail = "".join(f'<li><a href="#{item}">{escape(nodes[item]["title"])}</a></li>' for item in path if item != key)
    flag = '<p class="map-fiction">Fictional training example</p>' if fictional else ""
    back = f'<a href="#{parent}">Back one level</a>' if key != "overview" else ""
    return (
        f'<section class="map-screen" id="{key}" aria-labelledby="{key}-title">'
        f'<nav class="map-controls" aria-label="Map navigation">{back}<a href="#overview">Full map</a></nav>'
        f'<nav class="map-trail" aria-label="Map path"><ol>{trail}<li aria-current="page">{escape(title)}</li></ol></nav>'
        f'{flag}<h2 tabindex="-1" id="{key}-title">{escape(title)}</h2><p class="lead">{escape(summary)}</p>{body}</section>'
    )


def facts_list(facts):
    items = "".join(f'<div><dt>{escape(label)}</dt><dd>{escape(text)}</dd></div>' for label, text in facts)
    return f'<dl class="map-facts">{items}</dl>' if items else ""


def render_map(nodes):
    screens = []
    for key, node in nodes.items():
        path = breadcrumbs(nodes, key)
        sources = "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for label, href in node.get("links", []))
        body = facts_list(node.get("facts", []))
        if key == "overview":
            body += choice_cards(nodes, key, ENTRY_LABELS, ENTRY_LABELS) + diagram(nodes)
        elif choices := node.get("choices"):
            body += '<h3>Next choices</h3>' + choice_cards(nodes, key, (target for target, _ in choices))
        if sources:
            body += f'<h3>Sources and working documents</h3><ul class="map-sources">{sources}</ul>'
        screens.append(map_screen(nodes, key, node["title"], node["summary"], path, body, fictional=node.get("fictional", False)))
        for target, gate in node.get("choices", []):
            dest = nodes[target]
            body = facts_list(node.get("connection_evidence", {}).get(target, []))
            body += f'<p><a class="button outline" href="#{target}">Open {escape(dest["title"])}</a></p>'
            title = f'{node["title"]} → {dest["title"]}'
            screens.append(map_screen(nodes, edge_id(key, target), title, gate, path, body,
                                      fictional=node.get("fictional", False) or dest.get("fictional", False)))
    return (
        '<article class="map-deck" data-page-section="explore"><h1>Oversight maps</h1>'
        '<p class="map-intro">Public guide and fictional examples. Use authorized systems for confidential material.</p>'
        + "".join(screens) + "</article>"
    )
