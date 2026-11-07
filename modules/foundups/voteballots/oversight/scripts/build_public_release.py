"""Build the reviewed public accountability site from a preserved archive."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from verify_snapshot import safe_relative, verify


WORKSTREAM = Path(__file__).resolve().parents[1]
PUBLIC = WORKSTREAM / "public"
ARCHIVE = WORKSTREAM / "site"
DIRECTORY = WORKSTREAM.parent / "web"
PUBLIC_ASSETS = (
    "overview.css", "overview.js", "sw.js", "accountability.json", "llms.txt",
    "state-ag-transitions.json", "contact.css", "contact.js", "states-boundaries.json", "states-location.mjs",
)
DIRECTORY_ASSETS = ("contact-queue.mjs", "contact-roster.json")
APP_ASSETS = ("manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png", "icons/icon-512.png")
PAGES = {
    "legislative-roadmap": "Legislative roadmap",
    "contact": "Find and call your senators",
    "state-ag-transitions": "Attorney general transitions",
}
SECTIONS = (
    ("home", "Accountability"), ("legislative-roadmap", PAGES["legislative-roadmap"]),
    ("contact", "Call your senators"), ("hub", "Hub and spokes"), ("house", "House readiness"),
    ("senate", "Senate authority"), ("states", "State handoff"),
    ("state-ag-transitions", PAGES["state-ag-transitions"]), ("january-6", "January 6 record"),
    ("library", "Staff library"),
)
DOCUMENTS = {
    "00-executive-summary.html": "Accountability at a glance",
    "01-hub-and-authorities.html": "Committee authority and the shared hub",
    "02-state-referrals.html": "State jurisdiction and referrals",
    "03-financial-forensics.html": "Financial evidence methods",
    "04-jan6-and-readiness.html": "January 6 and staff readiness",
    "05-litigation-and-privilege.html": "Litigation and privilege",
    "11-house-first-pwa.html": "House readiness package",
    "14-worker-review-and-quality.html": "Evidence review checklist",
    "templates/appendix-a-house-rules.html": "Model House rules",
    "templates/appendix-b-legislative-purpose.html": "Legislative purpose memo",
    "templates/appendix-c-subpoena-and-wave-one.html": "Scoped evidence request",
    "templates/appendix-d-state-referral.html": "State referral packet",
    "templates/central-hub-charter.html": "Shared hub charter",
    "templates/committee-node-operating-plan.html": "Committee operating plan",
    "templates/evidentiary-report.html": "Evidence report",
    "templates/house-office-briefing.html": "House office briefing",
    "templates/staffing-and-recruitment-plan.html": "Staffing and recruitment plan",
}
STATUS = {
    "official_unofficial_lead": "Leader in official unofficial returns",
    "reported_projection": "Reported or announced transition",
    "certified": "Certified result",
    "unresolved": "Unresolved",
}
INTERNAL_MARKERS = re.compile(
    rb"found[ -]?ups?\b|voteballots|openclaw|chatgpt|\b0102\b|\bwsp[ -]?\d+|"
    rb"orchestrator_prompt|oversight-hub-pwa\.undaodu|vote\.mtrout\.com|github",
    re.I,
)
DRAFT_PARAGRAPHS = {
    "02-state-referrals.html": {
        "The public tracker records only": "Any public report should distinguish a referral, an investigation, charges and a disposition. Include corrections and contrary records. The receiving office controls its official announcements.",
    },
    "03-financial-forensics.html": {
        "The release pipeline creates": "Any authorized publication should use a separate reviewed export. Check disclosure authority, source permissions, witness security, personal information, contrary evidence and the accuracy of each reported relationship before release.",
    },
    "04-jan6-and-readiness.html": {
        "one of three proven root causes": "Sequential document demands consume time in a short Congress. Prepare the record map, custodian list, scope options, preservation terms and litigation analysis before issuance. Once the committee is constituted and has adopted applicable rules, its authorized decision-maker can evaluate appropriately tailored demands together.",
    },
    "templates/appendix-d-state-referral.html": {
        "the public tracker": "Any authorized public report should use the approved release record and distinguish a referral from an investigation or disposition.",
    },
}


def source(name: str) -> str:
    return (PUBLIC / name).read_text("utf-8")


def links(items: dict[str, str]) -> str:
    return "".join(f'<li><a href="/{path}">{escape(title)}</a></li>' for path, title in items.items())


def render(title: str, content: str, *, home: bool = False, asset_base: str = "./", contact: bool = False) -> bytes:
    nav = []
    for id_, label in SECTIONS:
        href = asset_base + id_ if id_ in PAGES else ("" if home else asset_base) + "#" + id_
        nav.append(f'<a href="{href}" data-section="{id_}">{escape(label)}</a>')
    page_assets = (
        f'<link rel="stylesheet" href="{asset_base}contact.css">\n'
        f'  <script type="module" src="{asset_base}contact.js"></script>'
        if contact else ""
    )
    page = source("index.html")
    for key, value in {
        "TITLE": escape(title), "NAV_LINKS": "\n".join(nav), "CONTENT": content, "ASSET_BASE": asset_base,
        "PAGE_ASSETS": page_assets,
    }.items():
        page = page.replace("{{" + key + "}}", value)
    return page.encode("utf-8")


def https_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Public sources must use a direct HTTPS URL")
    return escape(value, quote=True)


def render_transitions() -> bytes:
    data = json.loads(source("state-ag-transitions.json"))
    if data["schema_version"] != 1:
        raise ValueError("Unknown transition schema")
    checked = date.fromisoformat(data["as_of"])
    election = date.fromisoformat(data["election_date"])
    if checked < election:
        raise ValueError("Transition review predates the election")
    rows = []
    states = set()
    for row in data["rows"]:
        jurisdiction = row["jurisdiction"]
        if not jurisdiction or jurisdiction in states or not row["name"]:
            raise ValueError("Invalid or duplicate jurisdiction")
        states.add(jurisdiction)
        authority = ""
        if row.get("election_authority_url"):
            authority = f'<a href="{https_url(row["election_authority_url"])}">Election authority</a>'
        rows.append(
            f'<li><h3>{escape(jurisdiction)}</h3><p><strong>{escape(row["name"])}</strong><br>'
            f'<span class="status">{STATUS[row["status"]]}</span></p>'
            f'<a href="{https_url(row["result_url"])}">{escape(row["result_label"])}</a>'
            f'{authority}<a href="{https_url(row["office_url"])}">Current official office</a></li>'
        )
    label = f"{checked.day} {checked:%B %Y}"
    return render("Attorney general transitions", f"""
<section class="staff-section" id="ag-transitions" data-page-section="state-ag-transitions">
  <p class="kicker">STATE AND TERRITORIAL OFFICES</p>
  <h1>2026 attorney general transitions</h1>
  <p class="lead">Snapshot checked <time datetime="{checked}">{label}</time>. {escape(data["scope"])}</p>
  <p>Official unofficial leads and reported calls are provisional. An election result does not transfer authority. Use the current official office for any authorized correspondence until the transition is confirmed.</p>
  <p><a href="./#states">Return to state referral guidance</a> · <a href="/state-ag-transitions.json">Download the source-linked snapshot</a></p>
  <ul class="transition-list">{"".join(rows)}</ul>
</section>
""")


def render_staff_document(path: str, title: str) -> bytes:
    house_materials = {key: value for key, value in DOCUMENTS.items() if key.startswith("templates/") and "briefing" not in key}
    summaries = {
        "00-executive-summary.html": "<p>Use the roadmap to document a lead, identify committee authority, review the evidence, and decide what action the committee may take independently of DOJ. Consider a separate referral when state law supports one.</p><p><a href='/legislative-roadmap'>Open the legislative roadmap</a></p>",
        "11-house-first-pwa.html": "<p>Confirm the committee’s jurisdiction and legislative purpose. Assign responsible counsel, specify how evidence will be held and reviewed, and determine which requests may be issued. Each model below requires approval by an authorized office.</p><ul>" + links(house_materials) + "</ul>",
        "14-worker-review-and-quality.html": "<ol><li>Record the original source, date and exact locator.</li><li>Separate the documented item from interpretation and unresolved gaps.</li><li>Check amendments, contradictory records and alternative explanations.</li><li>Have a second reviewer confirm the evidence and counsel approve any disclosure.</li><li>Preserve the review and correction history.</li></ol><p><a href='/templates/evidentiary-report.html'>Open the evidence report template</a></p>",
        "templates/house-office-briefing.html": "<p>Identify the legislative question, the committee with jurisdiction, the evidence needed and the approval path. Counsel should confirm disclosure restrictions and any authority needed before a referral.</p><p><a href='/11-house-first-pwa.html'>Open the House readiness package</a></p>",
    }
    if path in summaries:
        content = f"<h1>{escape(title)}</h1>" + summaries[path]
    else:
        original = (ARCHIVE / "dist" / safe_relative(path)).read_text("utf-8")
        content = original.split("<main>", 1)[1].split("</main>", 1)[0]
        for phrase, replacement in DRAFT_PARAGRAPHS.get(path, {}).items():
            content = re.sub(
                r"<p>(?:(?!</p>).)*" + re.escape(phrase) + r"(?:(?!</p>).)*</p>",
                lambda _: f"<p>{escape(replacement)}</p>", content, flags=re.I | re.S,
            )
        replacements = {
            "A public GitHub repository and collaborative public Drive folder": "Public channels",
            "A public GitHub issue is never an intake channel for protected evidence.": "Keep protected evidence in approved channels.",
            "The operational term <strong>referral layer</strong> replaces any suggestion that prosecutors can simply “peel off” an established congressional criminal case.": "A referral sends screened material to an office with its own legal authority.",
            "The constitutional advantage is narrower than the slogan “pardon-proof.” ": "",
            " The public contributor network researches public records and submits documented leads; it exercises no compulsory powers.": "",
            " The public project performs public tracing and drafts an evidence gap; it does not impersonate law enforcement or contact a custodian under fictitious authority.": "",
            "The public project should record": "Any public account should state",
            "neither an agent nor a contributor": "no unauthorized person",
            "No agent is authorized by this playbook to move funds, sign wallet messages, access private accounts, evade controls, or execute a freeze.": "",
            "Public agents may retrieve and cite": "Public records may be retrieved and cited",
            "never treat it as an agent power": "reserve it for the chamber",
            "a social platform or a public agent network": "a social platform or an unapproved service",
            "or crowdsourced agent network": "or other unapproved service",
            " by an agent.": " from an incomplete record.",
            "A citizen repository, AI agent, transition team, or unorganized committee": "A person or office without issuing authority",
            "�g": "“", "�h": "”", "�fs": "’s", "�f": "’", "�i": "(", "�j": ")",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        first, sep, tail = content.partition("</h1>")
        content = first + sep + tail.replace("<h1>", "<h2>").replace("</h1>", "</h2>")
        content = re.sub(
            r"<table>\s*<tbody>\s*<tr>(.*?)</tr>",
            lambda m: "<table><thead><tr>"
            + m[1].replace("<td>", '<th scope="col">').replace("</td>", "</th>")
            + "</tr></thead><tbody>",
            content, flags=re.S,
        )
        content = content.replace("<table>", '<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable table"><table>')
        content = content.replace("</table>", "</table></div>")
    section = "house" if path in ("11-house-first-pwa.html", "templates/house-office-briefing.html") else "library"
    return render(title, f'<article class="legal-document" data-page-section="{section}">{content}</article>', asset_base="/")


def stage_release(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Release staging must use a new directory")
    snapshot = verify()
    if not snapshot["ok"]:
        raise ValueError("Historical Oversight snapshot failed verification")

    overview = source("overview.html").replace("{{LIBRARY_LINKS}}", links(DOCUMENTS))
    shared = {
        **{name: source(name).encode("utf-8") for name in PUBLIC_ASSETS},
        **{name: (DIRECTORY / name).read_bytes() for name in DIRECTORY_ASSETS},
        **{name: (ARCHIVE / "dist" / name).read_bytes() for name in APP_ASSETS},
        "index.html": render("Congressional accountability", overview, home=True),
        "state-ag-transitions.html": render_transitions(),
        "legislative-roadmap.html": render(PAGES["legislative-roadmap"], source("legislative-roadmap.html")),
        "contact.html": render(PAGES["contact"], source("contact.html"), contact=True),
    }
    files = {".openai/hosting.json": (ARCHIVE / ".openai/hosting.json").read_bytes()}
    for prefix in ("dist/", "dist/web/"):
        files.update({prefix + name: data for name, data in shared.items()})
    files.update({"dist/" + name: render_staff_document(name, title) for name, title in DOCUMENTS.items()})
    files["dist/LICENSE"] = (ARCHIVE / "dist/LICENSE").read_bytes()

    for name, data in files.items():
        if Path(name).suffix not in (".png", ".svg") and (INTERNAL_MARKERS.search(data) or b"\xef\xbf\xbd" in data):
            raise ValueError(f"Review internal or malformed content in {name}")

    output.mkdir(parents=True)
    for name, data in files.items():
        target = output / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    digest = hashlib.sha256(
        "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())).encode()
    ).hexdigest()
    return {"files": len(files), "baseline_files": snapshot["file_count"], "sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(stage_release(parser.parse_args().output), sort_keys=True))
