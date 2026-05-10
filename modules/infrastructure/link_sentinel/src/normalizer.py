"""Link Sentinel - URL Normalizer

Status: POC_IMPLEMENTED
WSP: 97 (Truth Boundaries)

Static URL normalization only. No network calls.
"""

from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, unquote
import re


def normalize_url(raw_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Normalize URL to canonical form.

    Returns:
        Tuple of (normalized_url, error_message, scheme)
        If error_message is not None, normalized_url will be None.
    """
    if not raw_url or not raw_url.strip():
        return None, "empty_url", None

    url = raw_url.strip()

    # First, check for known non-http schemes BEFORE adding https://
    # This prevents mangling javascript:, data:, file:, etc.
    non_http_schemes = {"javascript", "data", "file", "ftp", "mailto", "tel", "ssh", "git"}
    for scheme_prefix in non_http_schemes:
        if url.lower().startswith(f"{scheme_prefix}:"):
            # Parse as-is, don't add https://
            try:
                parsed = urlparse(url)
                scheme = parsed.scheme.lower()
                # For non-http schemes, return the original URL as-is
                # with unsupported_scheme hint
                return url, "unsupported_scheme", scheme
            except Exception:
                return None, "invalid_url", scheme_prefix

    # Handle scheme-relative URLs
    if url.startswith("//"):
        url = "https:" + url

    # Handle missing scheme (default to https)
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return None, "invalid_url", None

    scheme = (parsed.scheme or "").lower()

    # Check for unsupported schemes after parsing
    if scheme not in {"http", "https"}:
        return url, "unsupported_scheme", scheme

    # Normalize host
    host = (parsed.hostname or "").lower().strip()
    if not host:
        return None, "missing_host", scheme

    # Remove trailing dot from host
    host = host.rstrip(".")

    # Remove www. prefix for normalization
    normalized_host = host
    if normalized_host.startswith("www."):
        normalized_host = normalized_host[4:]

    # Normalize port (remove default ports)
    try:
        port = parsed.port
    except ValueError:
        # Invalid port format
        return None, "invalid_url", scheme

    if scheme == "http" and port == 80:
        port = None
    elif scheme == "https" and port == 443:
        port = None

    # Build netloc
    netloc = normalized_host
    if port:
        netloc = f"{normalized_host}:{port}"

    # Normalize path
    path = parsed.path or "/"
    if not path:
        path = "/"

    # Decode percent-encoding where safe, then re-encode
    try:
        path = unquote(path)
    except Exception:
        pass

    # Remove redundant slashes
    while "//" in path:
        path = path.replace("//", "/")

    # Normalize query (sort parameters)
    query = parsed.query
    if query:
        try:
            params = parse_qsl(query, keep_blank_values=True)
            params.sort(key=lambda x: x[0])
            query = urlencode(params)
        except Exception:
            pass

    # Rebuild URL
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        "",  # params
        query,
        ""   # fragment (removed for normalization)
    ))

    return normalized, None, scheme


def decode_punycode(host: str) -> Tuple[str, bool]:
    """Decode punycode domain to Unicode.

    Returns:
        Tuple of (decoded_host, is_punycode)
    """
    if not host:
        return host, False

    # Check if any label is punycode (starts with xn--)
    labels = host.split(".")
    is_punycode = any(label.lower().startswith("xn--") for label in labels)

    if not is_punycode:
        return host, False

    try:
        # Decode IDNA
        decoded = host.encode("ascii").decode("idna")
        return decoded, True
    except (UnicodeError, UnicodeDecodeError):
        # If decoding fails, return original
        return host, True


def extract_tld(host: str) -> Optional[str]:
    """Extract TLD from hostname.

    Simple extraction - just takes the last dot-separated segment.
    Does not handle multi-part TLDs like .co.uk.
    """
    if not host:
        return None

    parts = host.rstrip(".").split(".")
    if len(parts) < 2:
        return None

    return parts[-1].lower()


def count_subdomains(host: str) -> int:
    """Count subdomain depth.

    Example: a.b.c.example.com has depth 3 (a, b, c)
    """
    if not host:
        return 0

    parts = host.rstrip(".").split(".")

    # At minimum need domain.tld
    if len(parts) <= 2:
        return 0

    # Everything except domain.tld is subdomain
    return len(parts) - 2
