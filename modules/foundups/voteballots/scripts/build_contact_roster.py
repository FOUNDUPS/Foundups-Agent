"""Export a dated congressional office directory from official public XML."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen
import xml.etree.ElementTree as ET


HOUSE_URL = "https://clerk.house.gov/xml/lists/MemberData.xml"
SENATE_URL = "https://www.senate.gov/general/contact_information/senators_cfm.xml"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
OUTPUT = Path(__file__).resolve().parents[1] / "web" / "contact-roster.json"


def read_source(url, root_tag):
    with urlopen(url, timeout=20) as response:
        if response.geturl() != url:
            raise ValueError(f"Unexpected redirect for {url}")
        body = response.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES or re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", body, re.I):
        raise ValueError(f"Unsafe or oversized XML from {url}")
    root = ET.fromstring(body)
    if root.tag != root_tag:
        raise ValueError(f"Unexpected XML structure from {url}")
    return root, hashlib.sha256(body).hexdigest()


def office_record(member_id, name, chamber, state, district, phone):
    if not re.fullmatch(r"[A-Z][0-9]{6}", member_id):
        return None
    if not name or not re.fullmatch(r"[A-Z]{2}", state):
        raise ValueError(f"Missing name or state for {member_id}")
    match = re.fullmatch(r"(?:\(202\)|202)[ .-]*([2-9][0-9]{2})[ .-]*([0-9]{4})", phone)
    return {
        "id": member_id,
        "name": name,
        "chamber": chamber,
        "state": state,
        "district": district,
        "phone": "202" + "".join(match.groups()) if match else None,
    }


def build_roster():
    house, house_sha = read_source(HOUSE_URL, "MemberData")
    senate, senate_sha = read_source(SENATE_URL, "contact_information")
    house_members = house.findall("./members/member")
    senate_members = senate.findall("./member")
    if not 400 <= len(house_members) <= 450 or not 90 <= len(senate_members) <= 100:
        raise ValueError("Source counts are outside expected congressional ranges")
    congress = house.findtext("./title-info/congress-num", "")
    if not re.fullmatch(r"[0-9]{2,3}", congress):
        raise ValueError("Congress number missing from House roster")

    states = {}
    offices = []
    for member in house_members:
        info = member.find("./member-info")
        state = info.find("./state")
        code = state.attrib["postal-code"]
        states[code] = state.findtext("./state-fullname")
        record = office_record(
            info.findtext("bioguideID", "").strip(),
            info.findtext("official-name", "").strip(),
            "House",
            code,
            info.findtext("district", "").strip(),
            info.findtext("phone", "").strip(),
        )
        if record:
            offices.append(record)
    for member in senate_members:
        record = office_record(
            member.findtext("bioguide_id", "").strip(),
            " ".join(member.findtext(field, "").strip() for field in ("first_name", "last_name")).strip(),
            "Senate",
            member.findtext("state", "").strip(),
            "",
            member.findtext("phone", "").strip(),
        )
        if record:
            offices.append(record)
    if len({office["id"] for office in offices}) != len(offices):
        raise ValueError("Duplicate congressional office ID")
    if any(not states.get(office["state"]) for office in offices):
        raise ValueError("A listed office has no state or territory label")

    snapshot = {
        "schemaVersion": 1,
        "retrievedOn": datetime.now(timezone.utc).date().isoformat(),
        "congress": int(congress),
        "sources": [
            {"chamber": "House", "url": HOUSE_URL, "sha256": house_sha, "sourceRows": len(house_members)},
            {"chamber": "Senate", "url": SENATE_URL, "sha256": senate_sha, "sourceRows": len(senate_members)},
        ],
        "states": dict(sorted(states.items(), key=lambda item: item[1])),
    }
    offices.sort(key=lambda office: (office["state"], office["chamber"], office["name"]))
    return snapshot, offices


if __name__ == "__main__":
    metadata, offices = build_roster()
    prefix = json.dumps(metadata, ensure_ascii=False, indent=2)
    rows = ",\n".join("    " + json.dumps(office, ensure_ascii=False) for office in offices)
    OUTPUT.write_text(prefix[:-2] + ',\n  "offices": [\n' + rows + "\n  ]\n}\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(offices)} office rows to {OUTPUT.name}")
