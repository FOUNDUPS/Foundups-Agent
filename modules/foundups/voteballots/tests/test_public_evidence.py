"""Check the static Vote evidence page without using the mock FEC adapter.

Run pytest for the offline contract. To also verify every displayed amount
against the original electronic filings, run from the repository root:

python -B -m modules.foundups.voteballots.tests.test_public_evidence
"""

import hashlib
import re
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from modules.foundups.voteballots.src.fec_adapter import ConfidenceLevel, FECSource

PAGE = Path(__file__).parents[1] / "web" / "evidence.html"
FILING_URL = r"https://docquery\.fec\.gov/dcdev/posted/([1-9][0-9]{5,7})\.fec"
OFFICES = {
    "schumer": ("S8NY00082", "C00346312"),
    "jeffries": ("H2NY10092", "C00503052"),
}
KINDS = {
    "direct": "Direct PAC contribution",
    "earmark": "Individual earmark forwarded by PAC",
}


class EvidencePage(HTMLParser):
    """Read only the semantic fields used in published funding items."""

    def __init__(self, markup):
        super().__init__()
        self.office = None
        self.record = None
        self.field = None
        self.items = []
        self.checked_on = None
        self.feed(markup)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "article":
            self.office = attrs.get("id")
        if tag == "time" and attrs.get("id") == "evidence-as-of":
            self.checked_on = date.fromisoformat(attrs["datetime"])
        if tag == "li" and attrs.get("class") == "funding-item":
            self.record = {**attrs, "office": self.office, "text": ""}
        if self.record is not None and tag in {"data", "time", "a", "code"}:
            assert tag not in self.record, f"Duplicate {tag} in evidence item"
            self.field = tag
            self.record[tag] = {**attrs, "text": ""}

    def handle_data(self, data):
        if self.record is not None:
            self.record["text"] += data
            if self.field:
                self.record[self.field]["text"] += data

    def handle_endtag(self, tag):
        if tag == self.field:
            self.field = None
        if tag == "li" and self.record is not None:
            self.items.append(self.record)
            self.record = None
        if tag == "article":
            self.office = None


def filing_source(item, checked_on):
    url = item["a"]["href"]
    match = re.fullmatch(FILING_URL, url)
    assert match, "A verified item must link its exact official electronic filing"
    filing_id = f"FEC-{match[1]}"
    assert item["a"]["text"] == f"{filing_id} electronic filing"
    return FECSource(url=url, filing_id=filing_id, accessed_at=checked_on.isoformat())


def test_public_evidence_snapshot_contract():
    page = EvidencePage(PAGE.read_text(encoding="utf-8"))
    assert page.checked_on
    assert len(page.items) == 5
    assert {(item["office"], item["data-kind"]) for item in page.items} == {
        (office, kind) for office in OFFICES for kind in KINDS
    }
    assert len({item["code"]["text"] for item in page.items}) == len(page.items)
    for item in page.items:
        assert (item["data-candidate"], item["data-recipient"]) == OFFICES[item["office"]]
        assert item["data-filer"] == "C00797670"
        assert item["data-confidence"] == ConfidenceLevel.VERIFIED_FACT.value
        assert re.fullmatch(r"[0-9]{18}", item["data-image"])
        assert re.fullmatch(r"[0-9a-f]{64}", item["data-sha256"])
        assert re.fullmatch(r"[A-Z0-9]{20}", item["code"]["text"])
        assert "Verified" in item["text"] and KINDS[item["data-kind"]] in item["text"]
        assert "Schedule B, line 23" in item["text"]
        amount = Decimal(item["data"]["value"])
        assert amount > 0 and amount == Decimal(item["data"]["text"][1:].replace(",", ""))
        when = date.fromisoformat(item["time"]["datetime"])
        assert when <= page.checked_on
        assert item["time"]["text"] == f"{when:%B} {when.day}, {when.year}"
        election = item["data-election"]
        assert re.fullmatch(r"[GO]20[0-9]{2}", election)
        stage = "general election" if election[0] == "G" else "election designation: Other"
        assert f"{election[1:]} {stage}" in item["text"]
        filing_source(item, page.checked_on)


def verify_original_filings():
    """Recheck the pinned files. Emit only source IDs and counts."""
    test_public_evidence_snapshot_contract()
    page = EvidencePage(PAGE.read_text(encoding="utf-8"))
    filings = {}
    max_file_bytes = 8 * 1024 * 1024
    for item in page.items:
        source = filing_source(item, page.checked_on)
        if source.url not in filings:
            with urlopen(source.url, timeout=20) as response:
                assert response.geturl() == source.url, "Unexpected filing redirect"
                body = response.read(max_file_bytes + 1)
            assert 0 < len(body) <= max_file_bytes, source.filing_id
            filings[source.url] = body
        body = filings[source.url]
        assert hashlib.sha256(body).hexdigest() == item["data-sha256"], source.filing_id

        # FEC electronic filing Schedule B column order:
        # https://fecgov.github.io/fecfile-validate/SchB_spec.html
        rows = (line.split("\x1c") for line in body.decode("latin-1").split("\n"))
        tx = item["code"]["text"]
        matches = [row for row in rows if row[:3] == ["SB23", item["data-filer"], tx]]
        assert len(matches) == 1, (source.filing_id, tx)
        row = matches[0]
        assert row[5] == "CCM" and row[41] != "X", tx
        assert row[17] == item["data-election"], tx
        assert row[19] == item["time"]["datetime"].replace("-", ""), tx
        assert Decimal(row[20]) == Decimal(item["data"]["value"]), tx
        assert (row[24], row[26]) == (item["data-recipient"], item["data-candidate"]), tx
        purpose = row[22].strip().casefold()
        if item["data-kind"] == "direct":
            assert purpose == "contribution to committee" and not row[42].strip(), tx
        else:
            assert purpose.startswith("earmark of "), tx
    print(f"Verified {len(page.items)} records in {len(filings)} exact FEC filings.")


if __name__ == "__main__":
    verify_original_filings()
