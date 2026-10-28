# Validation

Run `python -B -m unittest discover -s tests` from the module root. Tests build
in an isolated temporary directory, inspect canonical/JSON-LD/CSP consistency,
check the public video field allowlist and verify pinned public asset contracts.
No network, form submission, deployment or third-party message is performed.

Privacy also requires review of actual diff content; passing tests cannot prove
that every sentence is suitable for public release. The imported build was
compared against all 17 content pages of the published-source snapshot.
