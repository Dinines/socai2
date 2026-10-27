"""Contract checks: don't confuse confidence, run status, or observed entities."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('export_alert_ui', Path(__file__).parents[1] / 'export_alert_ui.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ProjectionTest(unittest.TestCase):
    def setUp(self):
        self.alert = dict(id='a', tenant_id='t', title='test', description='description', severity='critical',
                          status='triaged', disposition='needs_review', ai_score=.85, confidence=80,
                          event_time='2026-10-25 00:00:00+00:00', created_at='2026-10-25 00:01:00+00:00',
                          affected_hosts=['server'], entities=[{'type':'host','value':'server'}],
                          enrichment_data={'socai2_fusion':{'incident_id':'incident-real','identity':{'source':'sensor','source_alert_id':'source-real'}}})
        self.snapshot = dict(alerts=[self.alert], runs=[], events=[], artifacts=[], costs=[], assets=[],
                             asset_links=[], owners=[], tenant_name='tenant-real')
        self.explain = {'a':dict(summary='returned summary', suggested_actions=[{'title':'check','rationale':'reason'}], generated_at='2026-10-25T00:02:00Z')}

    def test_severity_and_workflow_status(self):
        self.assertEqual([m.severity(x) for x in ['Critical','High','Medium','Low','Inform']], ['高','高','中','低','低'])
        for s in ['new','triaging','triaged']:self.assertEqual(m.status(s), 'New')
        self.assertEqual(m.status('triaged',True),'In progress')
        self.assertEqual(m.status('resolved',True),'Resolved')

    def test_real_fields_no_fabricated_fallbacks(self):
        result=m.project(self.snapshot,self.explain);a=result['alerts'][0];d=a['detailMaterial']
        self.assertEqual((d['risk'],d['confidence']['score']),(85,80))
        self.assertEqual((a['caseId'],a['owner'],a['incidentId']),(None,'未分配','incident-real'))
        self.assertEqual(result['assets'][0]['tags'],[])
        self.assertFalse(result['assets'][0]['inventory'])
        self.assertEqual(d['explanation']['summary'],'returned summary')
        self.assertEqual(d['explanation']['suggestedActions'][0]['title'],'check')
        self.assertNotIn('gaps',d['explanation'])
        self.assertEqual(d['responseRecommendations'],[])
        self.assertEqual([x['title'] for x in d['history']],['告警发生','告警入库'])
        self.assertEqual(d['timelineVersion'],2)

    def test_completed_alert_run_is_not_a_case_or_closed_alert(self):
        self.snapshot['runs']=[dict(id='r',case_id='a',raw_alert={'id':'a'},status='completed',created_at='2026-10-25T00:02:00Z',total_tokens=20)]
        self.snapshot['events']=[dict(run_id='r',kind='graph_step',ts='2026-10-25T00:03:00Z',agent='triage',summary='node done',payload={'node':'triage'})]
        a=m.project(self.snapshot,self.explain)['alerts'][0]
        self.assertEqual(a['status'],'In progress');self.assertIsNone(a['caseId'])
        self.assertEqual(a['detailMaterial']['runs'][0]['completion'],'unknown')

    def test_inventory_tags_only_from_asset_table(self):
        self.alert['tags']=['alert-only-tag'];self.alert['assigned_to_id']='u'
        self.snapshot['asset_links']=[{'alert_id':'a','asset_id':'inventory-id'}]
        self.snapshot['assets']=[{'id':'inventory-id','name':'Asset name','tags':['Windows 域控']}]
        self.snapshot['owners']=[{'id':'u','display_name':'Analyst'}]
        r=m.project(self.snapshot,self.explain)
        self.assertEqual(r['assets'][0]['tags'],['Windows 域控'])
        self.assertEqual(r['alerts'][0]['owner'],'Analyst')
        self.assertEqual(r['alerts'][0]['status'],'New')

    def test_missing_incident_rejected(self):
        self.alert['enrichment_data']={}
        with self.assertRaises(ValueError):m.project(self.snapshot,self.explain)


if __name__=='__main__':unittest.main()
