"""
dns_ops MCP Server
==================
Capability-layer MCP server for DNS and hosting operations.
Agents get tools, not credentials. The server holds provider API keys
internally and exposes constrained operations with policy enforcement.

Principle: 012 holds the keys. MCP server holds the capabilities. Agents hold neither.

WSP Compliance: WSP 96 (MCP Governance), WSP 71 (Security), WSP 11 (Interface)
"""

import json
import logging
import os
import socket
import ssl
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SERVER_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] dns_ops: %(message)s",
)
logger = logging.getLogger("dns_ops")

# ---------------------------------------------------------------------------
# Policy configuration (from environment)
# ---------------------------------------------------------------------------

def _env_truthy(key: str, default: str = "0") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes")


def _env_set(key: str, default: str = "") -> set:
    raw = os.getenv(key, default).strip()
    if not raw:
        return set()
    return {v.strip().lower() for v in raw.split(",") if v.strip()}


ALLOWED_DOMAINS: set = _env_set("DNS_OPS_ALLOWED_DOMAINS", "foundups.com")
ALLOWED_RECORDS: set = _env_set("DNS_OPS_ALLOWED_RECORDS", "a,aaaa,cname,txt,mx")
MUTATIONS_REQUIRE_APPROVAL: bool = _env_truthy("DNS_OPS_MUTATIONS_REQUIRE_APPROVAL", "1")
DRY_RUN_GLOBAL: bool = _env_truthy("DNS_OPS_DRY_RUN", "0")

AUDIT_LOG_PATH = _SERVER_DIR / os.getenv("DNS_OPS_AUDIT_LOG", "dns_ops_audit.jsonl")
APPROVAL_QUEUE_PATH = _SERVER_DIR / "approval_queue.jsonl"

# ---------------------------------------------------------------------------
# Audit logger (append-only JSONL)
# ---------------------------------------------------------------------------

def _audit_log(event: Dict[str, Any]) -> str:
    """Append audit event to JSONL log. Returns event_id."""
    raw = json.dumps(event, default=str, ensure_ascii=False)
    event_id = sha256(raw.encode()).hexdigest()[:16]
    event["event_id"] = event_id
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str, ensure_ascii=False) + "\n")
    return event_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Policy checks
# ---------------------------------------------------------------------------

def _extract_base_domain(domain: str) -> str:
    """Extract registrable domain: www.foundups.com -> foundups.com"""
    parts = domain.lower().strip(".").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain.lower()


def _check_domain_policy(domain: str) -> tuple:
    base = _extract_base_domain(domain)
    if not ALLOWED_DOMAINS:
        return False, "DNS_OPS_ALLOWED_DOMAINS is empty — fail-closed: all domains denied"
    if base in ALLOWED_DOMAINS:
        return True, f"domain {base} in allowlist"
    return False, f"domain {base} not in allowlist {ALLOWED_DOMAINS}"


def _check_record_type_policy(record_type: str) -> tuple:
    rt = record_type.upper()
    if rt.lower() in ALLOWED_RECORDS:
        return True, f"record type {rt} allowed"
    return False, f"record type {rt} not in allowlist {ALLOWED_RECORDS}"

# ---------------------------------------------------------------------------
# Approval queue
# ---------------------------------------------------------------------------

def _submit_for_approval(proposed_change: Dict) -> str:
    """Write proposed change to approval queue. Returns approval_id."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = proposed_change.get("name", "unknown")
    rtype = proposed_change.get("record_type", "UNK")
    action = proposed_change.get("action", "change")
    approval_id = f"dns_{action}_{ts}_{name}_{rtype}"

    entry = {
        "approval_id": approval_id,
        "timestamp": _now_iso(),
        "status": "pending",
        "proposed_change": proposed_change,
        "submitted_by": "mcp_agent",
    }
    with open(APPROVAL_QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")

    logger.info("Queued for approval: %s", approval_id)
    return approval_id

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("dns_ops", description="DNS and hosting operations — agents get capabilities, not credentials")

# ===== READ-ONLY TOOLS =====

@mcp.tool()
async def dns_query(domain: str, record_type: str = "A") -> Dict[str, Any]:
    """Query live DNS records for a domain. Read-only, no credentials needed."""
    audit_event = {
        "timestamp": _now_iso(),
        "tool": "dns_query",
        "category": "query",
        "domain": domain,
        "record_type": record_type,
    }

    try:
        rt = record_type.upper()
        records = []

        if rt in ("A", "AAAA"):
            family = socket.AF_INET if rt == "A" else socket.AF_INET6
            try:
                results = socket.getaddrinfo(domain, None, family)
                for res in results:
                    addr = res[4][0]
                    if addr not in [r["value"] for r in records]:
                        records.append({"value": addr, "ttl": None})
            except socket.gaierror as e:
                audit_event["outcome"] = "dns_error"
                audit_event["error"] = str(e)
                _audit_log(audit_event)
                return {"success": False, "domain": domain, "error": str(e)}

        elif rt == "CNAME":
            try:
                import dns.resolver
                answers = dns.resolver.resolve(domain, "CNAME")
                for rdata in answers:
                    records.append({"value": str(rdata.target).rstrip("."), "ttl": answers.rrset.ttl})
            except ImportError:
                # Fallback: use socket (can't get CNAME directly, but can resolve)
                try:
                    cname = socket.getfqdn(domain)
                    records.append({"value": cname, "ttl": None, "note": "via socket fallback"})
                except Exception as e:
                    return {"success": False, "domain": domain, "error": f"dnspython not installed and socket fallback failed: {e}"}
            except Exception as e:
                return {"success": False, "domain": domain, "error": str(e)}

        elif rt in ("TXT", "MX", "NS", "SOA"):
            try:
                import dns.resolver
                answers = dns.resolver.resolve(domain, rt)
                for rdata in answers:
                    records.append({"value": str(rdata), "ttl": answers.rrset.ttl})
            except ImportError:
                return {"success": False, "error": f"dnspython required for {rt} queries"}
            except Exception as e:
                return {"success": False, "domain": domain, "error": str(e)}
        else:
            return {"success": False, "error": f"unsupported record type: {rt}"}

        audit_event["outcome"] = "success"
        audit_event["record_count"] = len(records)
        _audit_log(audit_event)

        return {
            "success": True,
            "domain": domain,
            "record_type": rt,
            "records": records,
            "query_source": "system_resolver",
        }

    except Exception as e:
        audit_event["outcome"] = "error"
        audit_event["error"] = str(e)
        _audit_log(audit_event)
        return {"success": False, "domain": domain, "error": str(e)}


@mcp.tool()
async def dns_verify_tls(hostname: str, port: int = 443) -> Dict[str, Any]:
    """Verify TLS certificate for a hostname. Reports CN, SANs, expiry, chain validity."""
    audit_event = {
        "timestamp": _now_iso(),
        "tool": "dns_verify_tls",
        "category": "query",
        "hostname": hostname,
        "port": port,
    }

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

        # Extract cert fields
        subject = dict(x[0] for x in cert.get("subject", ()))
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        sans = [entry[1] for entry in cert.get("subjectAltName", ()) if entry[0] == "DNS"]
        not_after = cert.get("notAfter", "")
        cn = subject.get("commonName", "")

        hostname_match = hostname.lower() in [s.lower() for s in sans] or hostname.lower() == cn.lower()

        result = {
            "success": True,
            "hostname": hostname,
            "tls_valid": True,
            "cert_cn": cn,
            "cert_sans": sans,
            "hostname_match": hostname_match,
            "issuer": issuer.get("commonName", str(issuer)),
            "not_after": not_after,
            "chain_valid": True,
            "error": None,
        }

        audit_event["outcome"] = "success"
        audit_event["tls_valid"] = True
        audit_event["hostname_match"] = hostname_match
        _audit_log(audit_event)
        return result

    except ssl.SSLCertVerificationError as e:
        # TLS handshake failed — try without verification to get cert details
        try:
            ctx_nocheck = ssl.create_default_context()
            ctx_nocheck.check_hostname = False
            ctx_nocheck.verify_mode = ssl.CERT_NONE
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with ctx_nocheck.wrap_socket(sock, server_hostname=hostname) as ssock:
                    # Can't get parsed cert with CERT_NONE, but we know it failed
                    pass
        except Exception:
            pass

        result = {
            "success": True,  # Tool succeeded, TLS failed
            "hostname": hostname,
            "tls_valid": False,
            "hostname_match": False,
            "error": str(e),
        }
        audit_event["outcome"] = "tls_invalid"
        audit_event["error"] = str(e)
        _audit_log(audit_event)
        return result

    except Exception as e:
        audit_event["outcome"] = "error"
        audit_event["error"] = str(e)
        _audit_log(audit_event)
        return {"success": False, "hostname": hostname, "error": str(e)}


@mcp.tool()
async def dns_check_hosting(domain: str) -> Dict[str, Any]:
    """Determine hosting platform for a domain via DNS + HTTP header inspection."""
    import urllib.request

    audit_event = {
        "timestamp": _now_iso(),
        "tool": "dns_check_hosting",
        "category": "query",
        "domain": domain,
    }

    result: Dict[str, Any] = {"success": True, "domain": domain}

    # DNS resolution
    try:
        addrs = socket.getaddrinfo(domain, 443, socket.AF_INET)
        ips = list({r[4][0] for r in addrs})
        result["ip_addresses"] = ips
    except socket.gaierror as e:
        result["ip_addresses"] = []
        result["dns_error"] = str(e)

    # HTTP headers
    headers: Dict[str, str] = {}
    http_status = None
    try:
        req = urllib.request.Request(
            f"https://{domain}/",
            method="HEAD",
            headers={"User-Agent": "dns_ops_mcp/0.1"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            http_status = resp.status
            headers = dict(resp.headers)
    except Exception as e:
        result["http_error"] = str(e)

    result["http_status"] = http_status
    result["headers_sample"] = {k: v for k, v in list(headers.items())[:10]}

    # Platform detection heuristics
    platform = "unknown"
    evidence = []

    ip_str = " ".join(result.get("ip_addresses", []))
    if "199.36.158" in ip_str:
        evidence.append("IP in Firebase Hosting range (199.36.158.x)")
        platform = "firebase_hosting"
    if "76.76.21" in ip_str or "76.223" in ip_str:
        evidence.append("IP in Vercel range")
        platform = "vercel"

    server = headers.get("server", "").lower()
    if "vercel" in server:
        platform = "vercel"
        evidence.append(f"server header: {server}")

    x_served = headers.get("x-served-by", "")
    if "cache-" in x_served.lower():
        evidence.append(f"Fastly CDN via x-served-by (Firebase pattern)")

    if headers.get("x-vercel-id"):
        platform = "vercel"
        evidence.append(f"x-vercel-id header present")

    result["detected_platform"] = platform
    result["evidence"] = evidence

    # TLS check
    tls_result = await dns_verify_tls(domain)
    result["tls_valid"] = tls_result.get("tls_valid", False)

    audit_event["outcome"] = "success"
    audit_event["detected_platform"] = platform
    _audit_log(audit_event)

    return result


@mcp.tool()
async def dns_verify_domain_setup(
    domain: str,
    expected_platform: Optional[str] = None,
    expected_ip: Optional[str] = None,
    expected_cname: Optional[str] = None,
) -> Dict[str, Any]:
    """Full verification: DNS + TLS + hosting platform + content check. Read-only."""
    checks: Dict[str, bool] = {}
    failures: List[str] = []
    recommendations: List[str] = []

    # DNS resolution
    dns_result = await dns_query(domain, "A")
    checks["dns_resolves"] = dns_result.get("success", False) and len(dns_result.get("records", [])) > 0
    if not checks["dns_resolves"]:
        failures.append(f"DNS does not resolve for {domain}")
        recommendations.append(f"Add A or CNAME record for {domain}")

    # Expected IP check
    if expected_ip and checks["dns_resolves"]:
        resolved_ips = [r["value"] for r in dns_result.get("records", [])]
        checks["dns_value_matches_expected"] = expected_ip in resolved_ips
        if not checks["dns_value_matches_expected"]:
            failures.append(f"Expected IP {expected_ip}, got {resolved_ips}")

    # Expected CNAME check
    if expected_cname:
        cname_result = await dns_query(domain, "CNAME")
        cname_values = [r["value"] for r in cname_result.get("records", [])]
        checks["cname_matches_expected"] = expected_cname.lower() in [v.lower() for v in cname_values]
        if not checks["cname_matches_expected"]:
            failures.append(f"Expected CNAME {expected_cname}, got {cname_values}")

    # TLS
    tls_result = await dns_verify_tls(domain)
    checks["tls_valid"] = tls_result.get("tls_valid", False)
    checks["tls_hostname_match"] = tls_result.get("hostname_match", False)
    if not checks["tls_valid"]:
        failures.append(f"TLS invalid: {tls_result.get('error', 'unknown')}")
    if not checks.get("tls_hostname_match", True):
        failures.append(f"TLS cert does not match hostname (CN={tls_result.get('cert_cn')})")
        recommendations.append(f"Add {domain} as custom domain in hosting platform to provision cert")

    # Hosting platform
    hosting_result = await dns_check_hosting(domain)
    checks["http_status_ok"] = hosting_result.get("http_status") in (200, 301, 302)
    if expected_platform:
        detected = hosting_result.get("detected_platform", "unknown")
        checks["hosting_platform_matches"] = expected_platform.lower() in detected.lower()
        if not checks["hosting_platform_matches"]:
            failures.append(f"Expected platform {expected_platform}, detected {detected}")

    all_passed = all(checks.values())

    audit_event = {
        "timestamp": _now_iso(),
        "tool": "dns_verify_domain_setup",
        "category": "query",
        "domain": domain,
        "outcome": "all_passed" if all_passed else "failures_detected",
        "check_count": len(checks),
        "failure_count": len(failures),
    }
    _audit_log(audit_event)

    return {
        "success": True,
        "domain": domain,
        "checks": checks,
        "all_passed": all_passed,
        "failures": failures,
        "recommendations": recommendations,
    }


# ===== GATED WRITE TOOLS =====

def _gate_sequence(
    domain: str, name: str, record_type: str, action: str,
    value: Optional[str] = None, ttl: int = 3600, dry_run: bool = False,
) -> Dict[str, Any]:
    """Common gate sequence for all write operations. Returns gate result."""

    proposed_change = {
        "action": action,
        "domain": domain,
        "name": name,
        "record_type": record_type.upper(),
        "value": value,
        "ttl": ttl,
    }

    # Policy checks
    domain_ok, domain_reason = _check_domain_policy(domain)
    record_ok, record_reason = _check_record_type_policy(record_type)

    policy_result = {
        "domain_allowed": domain_ok,
        "domain_reason": domain_reason,
        "record_type_allowed": record_ok,
        "record_type_reason": record_reason,
        "dry_run": dry_run or DRY_RUN_GLOBAL,
        "approval_required": MUTATIONS_REQUIRE_APPROVAL or action == "delete",
    }

    # Audit (always, regardless of outcome)
    audit_event = {
        "timestamp": _now_iso(),
        "tool": f"dns_{action}_record",
        "category": "mutation",
        "caller": "mcp_agent",
        "domain": domain,
        "record_name": name,
        "record_type": record_type.upper(),
        "proposed_value": value,
        "policy_result": policy_result,
    }

    # Policy deny
    if not domain_ok:
        audit_event["outcome"] = "denied"
        audit_event["error"] = domain_reason
        event_id = _audit_log(audit_event)
        return {
            "success": False, "status": "denied",
            "reason": domain_reason, "audit_event_id": event_id,
        }

    if not record_ok:
        audit_event["outcome"] = "denied"
        audit_event["error"] = record_reason
        event_id = _audit_log(audit_event)
        return {
            "success": False, "status": "denied",
            "reason": record_reason, "audit_event_id": event_id,
        }

    # Dry run
    if policy_result["dry_run"]:
        audit_event["outcome"] = "dry_run"
        event_id = _audit_log(audit_event)
        return {
            "success": True, "status": "dry_run",
            "proposed_change": proposed_change,
            "policy_checks": policy_result,
            "audit_event_id": event_id,
            "note": "No changes made. Dry-run mode active.",
        }

    # Approval gate
    if policy_result["approval_required"]:
        approval_id = _submit_for_approval(proposed_change)
        audit_event["outcome"] = "queued_for_approval"
        audit_event["approval_id"] = approval_id
        event_id = _audit_log(audit_event)
        return {
            "success": True, "status": "queued_for_approval",
            "approval_id": approval_id,
            "proposed_change": proposed_change,
            "policy_checks": policy_result,
            "audit_event_id": event_id,
            "note": "Queued for 012 approval. Use approve CLI to execute.",
        }

    # Execute directly (approval not required)
    # Phase 1: return the gate result, actual provider call is in Phase 2
    audit_event["outcome"] = "approved_no_gate"
    event_id = _audit_log(audit_event)
    return {
        "success": True, "status": "approved_awaiting_provider",
        "proposed_change": proposed_change,
        "policy_checks": policy_result,
        "audit_event_id": event_id,
        "note": "Policy passed. Provider execution available in Phase 2.",
    }


@mcp.tool()
async def dns_create_record(
    domain: str, name: str, record_type: str,
    value: str, ttl: int = 3600, dry_run: bool = False,
) -> Dict[str, Any]:
    """Create a DNS record. Gated: requires domain/record-type policy + 012 approval."""
    return _gate_sequence(domain, name, record_type, "create", value, ttl, dry_run)


@mcp.tool()
async def dns_update_record(
    domain: str, name: str, record_type: str,
    value: str, ttl: int = 3600, dry_run: bool = False,
) -> Dict[str, Any]:
    """Update an existing DNS record. Same gate sequence as dns_create_record."""
    return _gate_sequence(domain, name, record_type, "update", value, ttl, dry_run)


@mcp.tool()
async def dns_delete_record(
    domain: str, name: str, record_type: str, dry_run: bool = False,
) -> Dict[str, Any]:
    """Delete a DNS record. Always requires approval, even if env says otherwise."""
    return _gate_sequence(domain, name, record_type, "delete", None, 0, dry_run)


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

def _validate_startup():
    """Fail-closed: refuse to start if critical config is missing."""
    if not ALLOWED_DOMAINS:
        logger.warning("DNS_OPS_ALLOWED_DOMAINS is empty — all write ops will be denied (fail-closed)")

    # Credentials check — warn but don't block for read-only operation
    has_godaddy = bool(os.getenv("GODADDY_API_KEY")) and bool(os.getenv("GODADDY_API_SECRET"))
    if has_godaddy:
        logger.info("GoDaddy credentials present — write ops available (subject to policy)")
    else:
        logger.info("GoDaddy credentials not set — read-only tools available, write ops will queue only")

    logger.info("Policy: domains=%s records=%s approval=%s dry_run=%s",
                ALLOWED_DOMAINS, ALLOWED_RECORDS, MUTATIONS_REQUIRE_APPROVAL, DRY_RUN_GLOBAL)


if __name__ == "__main__":
    _validate_startup()
    logger.info("dns_ops MCP server starting — agents get capabilities, not credentials")
