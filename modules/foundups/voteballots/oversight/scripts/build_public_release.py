"""Stage the Oversight public overlay from the verified historical inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verify_snapshot import safe_relative, verify


WORKSTREAM = Path(__file__).resolve().parents[1]
PUBLIC = WORKSTREAM / "public"
OVERLAY_ASSETS = ("overview.css", "overview.js", "accountability.json", "llms.txt")
NAVIGATION_FILES = ("index.html", "sw.js")


def replace_once(content: bytes, before: bytes, after: bytes) -> bytes:
    if content.count(before) != 1:
        raise ValueError("Historical source differs from the reviewed overlay insertion point")
    return content.replace(before, after, 1)


def stage_release(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Release staging must use a new directory")
    snapshot = verify()
    if not snapshot["ok"]:
        raise ValueError("Historical Oversight snapshot failed verification")

    source = WORKSTREAM / "site"
    manifest = json.loads((WORKSTREAM / "source-snapshot.json").read_text("utf-8"))
    files = {
        entry["source_path"]: (source / safe_relative(entry["source_path"])).read_bytes()
        for entry in manifest["files"]
    }
    overview = (PUBLIC / "overview.html").read_bytes().replace(b"\r\n", b"\n").strip()
    for prefix in ("dist/", "dist/web/"):
        index = files[prefix + "index.html"]
        index = replace_once(index, b"120TH CONGRESS <span>", b"PLAN FOR 120TH CONGRESS <span>")
        index = replace_once(
            index,
            b"</head>",
            b'<link rel="stylesheet" href="overview.css"><link rel="alternate" '
            b'type="application/json" href="/accountability.json" title="Oversight project manifest"></head>',
        )
        index = replace_once(index, b'<div id="view"></div>', overview + b'\n<div id="view" hidden></div>')
        files[prefix + "index.html"] = replace_once(
            index, b"</body>", b'<script src="overview.js" defer></script></body>'
        )
        files[prefix + "sw.js"] = (PUBLIC / "sw.js").read_bytes().replace(b"\r\n", b"\n")
        for name in OVERLAY_ASSETS:
            files[prefix + name] = (PUBLIC / name).read_bytes().replace(b"\r\n", b"\n")

    for name in NAVIGATION_FILES + OVERLAY_ASSETS:
        if files["dist/" + name] != files["dist/web/" + name]:
            raise ValueError(f"Release root/web mirror differs: {name}")

    output.mkdir(parents=True)
    for name, data in files.items():
        path = output / safe_relative(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    digest = hashlib.sha256(
        "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())).encode()
    ).hexdigest()
    return {"files": len(files), "baseline_files": snapshot["file_count"], "sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(stage_release(parser.parse_args().output), sort_keys=True))
