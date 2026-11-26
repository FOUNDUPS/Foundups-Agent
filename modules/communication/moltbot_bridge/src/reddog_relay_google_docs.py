"""Adapt a host's existing Google Docs read capability to RelaySnapshot.

This module does not invoke cloud tools from Python or obtain credentials.
The admitted host supplies the actual native connector call and a scoped,
reviewed decoder; document text alone is never execution authority.
"""

from modules.communication.moltbot_bridge.src.reddog_relay_watcher import (
    RelaySnapshot, RelayUnavailable,
)


class GoogleDocsRelayReader:
    def __init__(self, read_document, decode_messages):
        if not callable(read_document) or not callable(decode_messages):
            raise ValueError("relay_document_binding_required")
        self.read_document = read_document
        self.decode_messages = decode_messages

    def __call__(self, source, previous_watermark, *, timeout_seconds):
        if source.provider != "google_docs":
            raise RelayUnavailable("WRONG_PROVIDER")
        # The host must call the existing get_document capability for this exact
        # ID, with all tabs and no partial fields projection, under this deadline.
        response = self.read_document(document_id=source.container,
                                      timeout_seconds=timeout_seconds)
        if not isinstance(response, dict) or response.get("isError"):
            raise RelayUnavailable("DOCUMENT_READ_UNAVAILABLE")
        document = response.get("structuredContent", response)
        if (not isinstance(document, dict)
                or document.get("documentId") != source.container
                or not isinstance(document.get("revisionId"), str)
                or not document["revisionId"]):
            raise RelayUnavailable("DOCUMENT_BINDING_OR_REVISION_MISSING")
        tabs = document.get("tabs")
        if not isinstance(tabs, list) or not tabs or len(tabs) > 100:
            raise RelayUnavailable("DOCUMENT_TABS_INCOMPLETE")
        ids = set()
        for tab in tabs:
            if (not isinstance(tab, dict) or not isinstance(tab.get("tabId"), str)
                    or not tab["tabId"] or tab["tabId"] in ids
                    or not isinstance(tab.get("body"), dict)
                    or not isinstance(tab["body"].get("content"), list)):
                raise RelayUnavailable("DOCUMENT_TABS_INCOMPLETE")
            ids.add(tab["tabId"])
        # Always decode the complete read, even at the same opaque revision:
        # unresolved messages may need immutable ID+digest refetch after restart.
        messages = self.decode_messages(document)
        return RelaySnapshot(source.key, document["revisionId"], messages, True)
