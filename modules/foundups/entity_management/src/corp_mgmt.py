"""Offline Corp Mgmt reconciliation PoC. No network, persistence or execution."""
def assess(record):
    required = ('entity_ref', 'jurisdiction', 'agency', 'period', 'role')
    missing = [key for key in required if not record.get(key)]
    if missing:
        return {'state': 'NEEDS_CONTEXT', 'missing': missing, 'can_execute': False}
    if record['role'] not in {'applicant', 'lessee', 'operator', 'signatory'}:
        return {'state': 'ROLE_UNVERIFIED', 'can_execute': False}
    blockers = []
    for gate in ('role_verified', 'filing_accepted', 'payment_applied'):
        if record.get(gate) is not True:
            blockers.append(gate)
    if record.get('joint_proposer_required') is True and record.get('joint_proposer_verified') is not True:
        blockers.append('joint_proposer_verified')
    if record.get('city_consultation_required') is True and record.get('city_consultation_completed') is not True:
        blockers.append('city_consultation_completed')
    return {'state': 'RECONCILED' if not blockers else 'NEEDS_EVIDENCE',
            'blockers': blockers, 'can_execute': False,
            'standing': record.get('standing', 'UNKNOWN'),
            'tax_balance': record.get('tax_balance', 'UNKNOWN'),
            'exemption': record.get('exemption', 'UNKNOWN'),
            'renewal': record.get('renewal', 'UNKNOWN')}
