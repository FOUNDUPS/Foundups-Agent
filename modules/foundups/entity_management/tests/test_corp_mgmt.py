import unittest
from modules.foundups.entity_management.src.corp_mgmt import assess
class TestCorpMgmt(unittest.TestCase):
    def fixture(self):
        return dict(entity_ref='SYNTHETIC_ENTITY',jurisdiction='TEST',agency='TEST',period='TEST',role='applicant',role_verified=True,filing_accepted=True,payment_applied=True)
    def test_payment_is_not_acceptance(self):
        r=self.fixture();r['filing_accepted']=False;r['bank_settled']=True
        self.assertIn('filing_accepted',assess(r)['blockers'])
    def test_role_required(self):
        r=self.fixture();r['role']='owner'
        self.assertEqual(assess(r)['state'],'ROLE_UNVERIFIED')
    def test_joint_proposer_not_bypassed(self):
        r=self.fixture();r['joint_proposer_required']=True;r['city_consultation_completed']=True
        self.assertIn('joint_proposer_verified',assess(r)['blockers'])
    def test_separate_statuses_and_no_authority(self):
        r=assess(self.fixture())
        self.assertEqual(r['state'],'RECONCILED');self.assertEqual(r['exemption'],'UNKNOWN');self.assertEqual(r['renewal'],'UNKNOWN');self.assertFalse(r['can_execute'])
    def test_incomplete_entity(self):
        self.assertEqual(assess({})['state'],'NEEDS_CONTEXT')
if __name__=='__main__':unittest.main()
