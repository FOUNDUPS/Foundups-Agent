"""Metadata-only external audit result classification ."""
from dataclasses import dataclass
import json


MAX_OUTPUT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class AuditSummary:
    tool: str
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    unrated: int = 0
    incomplete: int = 0


def _pip_counts(data):
    dependencies = data if isinstance(data, list) else data['dependencies']
    if not isinstance(dependencies, list):
        raise ValueError('invalid_dependencies')
    counts = {'unrated': 0, 'incomplete': 0}
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise ValueError('invalid_dependency')
        if dependency.get('skip_reason'):
            counts['incomplete'] += 1
        elif 'vulns' not in dependency:
            raise ValueError('missing_vulnerability_inventory')
        vulnerabilities = dependency.get('vulns', [])
        if not isinstance(vulnerabilities, list) or any(not isinstance(v, dict) for v in vulnerabilities):
            raise ValueError('invalid_vulnerability_inventory')
        counts['unrated'] += len(vulnerabilities)
    return counts


def _bandit_counts(data):
    results, errors = data['results'], data['errors']
    if not isinstance(results, list) or not isinstance(errors, list):
        raise ValueError('invalid_bandit_inventory')
    counts = {'high': 0, 'medium': 0, 'low': 0, 'incomplete': len(errors)}
    for issue in results:
        severity = issue['issue_severity']
        if severity not in {'HIGH', 'MEDIUM', 'LOW'}:
            raise ValueError('invalid_bandit_severity')
        counts[severity.lower()] += 1
    return counts


def _npm_counts(data):
    if data.get('error'):
        raise ValueError('npm_error')
    vulnerabilities = data['vulnerabilities']
    if not isinstance(vulnerabilities, dict):
        raise ValueError('invalid_npm_inventory')
    counts = dict.fromkeys(('critical', 'high', 'medium', 'low', 'info'), 0)
    for issue in vulnerabilities.values():
        severity = issue['severity']
        if severity not in {'critical', 'high', 'moderate', 'low', 'info'}:
            raise ValueError('invalid_npm_severity')
        counts['medium' if severity == 'moderate' else severity] += 1
    return counts


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def summarize_external_audit(tool, returncode, body):
    """Discard descriptions, code excerpts, reasons and arbitrary provider values."""
    parsers = {'pip-audit': _pip_counts, 'bandit': _bandit_counts, 'npm': _npm_counts}
    if tool not in parsers:
        raise ValueError('unknown_audit_tool')
    try:
        if type(returncode) is not int or returncode not in {0, 1}:
            raise ValueError('failed_audit_process')
        if type(body) is not bytes or not body or len(body) > MAX_OUTPUT_BYTES:
            raise ValueError('invalid_audit_output')
        counts = parsers[tool](json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=_unique_object))
        if returncode == 1 and not sum(counts.values()):
            counts['incomplete'] = 1
        return AuditSummary(tool, **counts)
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError, AttributeError):
        return AuditSummary(tool, incomplete=1)


def summary_findings(summary):
    """Use fixed tool names and integer totals only; never report response text."""
    findings = []
    if summary.incomplete:
        findings.append(f'SECURITY_SCAN_ERROR: {summary.tool} inspection incomplete ({summary.incomplete})')
    if summary.critical or summary.high or summary.unrated:
        findings.append(f'SECURITY_AUDIT_FAIL: {summary.tool} reports {summary.critical} critical, '
                        f'{summary.high} high and {summary.unrated} unrated known vulnerabilities')
    if summary.medium:
        findings.append(f'SECURITY_VULNERABILITY_MEDIUM: {summary.tool} reports {summary.medium}')
    if summary.low or summary.info:
        findings.append(f'SECURITY_VULNERABILITY_LOW: {summary.tool} reports '
                        f'{summary.low} low and {summary.info} informational findings')
    return findings
