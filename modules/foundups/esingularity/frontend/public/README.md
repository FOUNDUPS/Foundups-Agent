# eSingularity / YUMORI public assets

This directory is the canonical repository location for static assets published by the shared eSingularity.ai / YUMORI.me frontend.

## Official YUMORI.me QR code

**Canonical asset:** `YUMORIme-qr-code.png`

**Encoded destination:** `https://YUMORI.me`

This PNG is the official YUMORI.me QR-code asset for website, document, flyer, press, committee, and other project outputs. Reuse this file rather than creating or maintaining separate QR copies in page-specific, Drive-export, Sites-checkout, or legacy folders.

The asset was recovered from the former local `sites/yumori-language-sweep/public/YUMORIme-qr-code.png` checkout and copied unchanged into this canonical module. That legacy local checkout is not an authoring source and is not tracked as a parallel YUMORI.me site in the repository.

Rules:

- Preserve the filename `YUMORIme-qr-code.png` unless an intentional migration updates every consumer and this contract together.
- Do not regenerate the QR merely for styling; place the canonical PNG inside the surrounding design instead.
- Before publishing, verify that the QR decodes to exactly `https://YUMORI.me`.
- If the destination ever changes, treat that as a campaign-routing change: update the canonical asset, verify it, update this record and the YUMORI/eSingularity documentation in the same change.
- Derived PDFs, Google Docs, flyers and other exports may embed this image, but they do not become the source asset.

The canonical application remains `modules/foundups/esingularity`; YUMORI.me is a distinct movement homepage inside that FoundUp, not a second repository or legacy Sites tree.
