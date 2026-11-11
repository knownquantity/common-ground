import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from domain import Store, Invalid

def sample():
    quote='We might explore a workshop. I, Alex, will deliver a prototype by November 13, 2026.'
    ev=[{'source_id':'new','quote':quote}]
    return {'source':{'title':'Fictional Are.na pilot','text':quote,'source_date':'2026-11-11'},'record':{'name':'Fictional practitioner pilot','counterpart':'Are.na (fictional)','shared_goal':'Explore a workshop','goal_evidence':ev,'contributions':[{'side':'ours','text':'Prototype','status':'source-supported','evidence':ev}],'open_questions':['Workshop is not agreed.'],'commitments':[{'action':'Deliver prototype','owner':'Alex','side':'ours','due_date':'2026-11-13','date_wording':'November 13, 2026','status':'agreed','evidence':ev},{'action':'Explore workshop','owner':None,'side':'unresolved','due_date':None,'date_wording':None,'status':'proposed','evidence':ev}]}}

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'data.db'
        self.store=Store(sqlite3.connect(self.path),self.tmp.name)
    def tearDown(self): self.store.db.close();self.tmp.cleanup()
    def saved(self):
        p=self.store.prepare('capture',sample());self.store.apply(p['proposal_id'],'capture');return p['record']
    def update(self,r,note='Alex proposes November 20, 2026 instead.'):
        return {'source':{'title':'Fictional update','text':note,'source_date':'2026-11-12'},'collaboration_id':r['id'],'expected_revision':r['revision'],'commitment_changes':[{'id':r['commitments'][0]['id'],'due_date':'2026-11-20','date_wording':'November 20, 2026','evidence':[{'source_id':'new','quote':note}]}]}
    def test_preview_apply_retry_restart(self):
        p=self.store.prepare('capture',sample())
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM records').fetchone()[0],0)
        self.assertEqual(self.store.prepare('capture',sample())['proposal_id'],p['proposal_id'])
        self.store.apply(p['proposal_id'],'capture');self.store.apply(p['proposal_id'],'capture')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM history').fetchone()[0],1)
        code='import sqlite3,sys;from domain import Store; s=Store(sqlite3.connect(sys.argv[1]),sys.argv[2]);print(s.get(sys.argv[3])["name"])'
        run=subprocess.run([sys.executable,'-c',code,str(self.path),self.tmp.name,p['record']['id']],cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertIn('Fictional practitioner pilot',run.stdout)
        self.assertEqual(self.store.get(p['record']['id']),p['record'])
    def test_tentative_stays_proposed(self):
        r=self.saved();self.assertEqual(self.store.get(r['id'])['commitments'][1]['status'],'proposed')
    def test_evidence_and_dates_fail_without_writes(self):
        for mutate in [lambda p:p['record']['goal_evidence'][0].update(quote='invented'),lambda p:p['record']['commitments'][0].update(due_date='2026-02-30'),lambda p:p['record']['goal_evidence'][0].update(start=0,end=4),lambda p:p['record'].update(extra=True)]:
            p=sample();mutate(p)
            with self.assertRaises(Invalid): self.store.prepare('capture',p)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM proposals').fetchone()[0],0)
    def test_conflict_and_resolution_keep_history(self):
        r=self.saved();p=self.store.prepare('update',self.update(r));after=p['record']
        self.assertEqual(after['commitments'][0]['due_date'],'2026-11-13')
        self.store.apply(p['proposal_id'],'update')
        note='Alex confirms the deadline is now November 20, 2026.'
        u={'source':{'title':'Clarification','text':note},'collaboration_id':r['id'],'expected_revision':2,'resolve':[{'id':after['discrepancies'][0]['id'],'decision':'accept','evidence':[{'source_id':'new','quote':note}]}]}
        p=self.store.prepare('update',u);self.store.apply(p['proposal_id'],'update')
        result=self.store.query({'collaboration_id':r['id']})
        self.assertEqual(result['record']['commitments'][0]['due_date'],'2026-11-20')
        self.assertEqual(result['record']['commitments'][0]['id'],r['commitments'][0]['id'])
        self.assertEqual(len(result['history']),3)
        self.assertIn('2026-11-13',json.dumps(result['history']))
        self.assertEqual(len(result['record']['sources']),3)
    def test_stale_atomic_update(self):
        r=self.saved();a=self.store.prepare('update',self.update(r));b=self.store.prepare('update',self.update(r,'Alternative note with November 20, 2026.'))
        self.store.apply(a['proposal_id'],'update')
        with self.assertRaisesRegex(Invalid,'Stale'):self.store.apply(b['proposal_id'],'update')
        self.assertEqual(len(self.store.get(r['id'])['sources']),2)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM history').fetchone()[0],2)
    def test_completion_requires_note_and_evidence(self):
        r=self.saved();u=self.update(r,'Alex delivered the prototype.');u['commitment_changes'][0].pop('due_date');u['commitment_changes'][0].pop('date_wording');u['commitment_changes'][0]['status']='completed'
        p=self.store.prepare('update',u);self.store.apply(p['proposal_id'],'update')
        q=self.store.query({'side':'ours'},date(2026,11,14));self.assertEqual(len(q['completed']),1);self.assertFalse(q['overdue'])
        self.assertEqual(q['completed'][0]['evidence'],r['commitments'][0]['evidence'])
    def test_date_buckets_and_week(self):
        p=sample();base=p['record']['commitments'][0]
        for due,status,side in [('2026-11-10','agreed','ours'),(None,'agreed','ours'),('2026-11-13','agreed','theirs'),('2026-11-12','completed','ours'),('2026-11-12','cancelled','ours'),('2026-11-16','agreed','ours')]:
            c=copy.deepcopy(base);c.update(due_date=due,status=status,side=side);p['record']['commitments'].append(c)
        a=self.store.prepare('capture',p);self.store.apply(a['proposal_id'],'capture')
        q=self.store.query({'this_week':True,'side':'ours','timezone':'America/New_York'},date(2026,11,11))
        self.assertEqual((q['date_from'],q['date_to']),('2026-11-09','2026-11-15'))
        for k in ['overdue','upcoming','undated','completed','cancelled']:self.assertEqual(len(q[k]),1,k)
        self.assertEqual(len(self.store.query({'side':'theirs'},date(2026,11,11))['upcoming']),1)
        self.assertEqual(self.store.query({'this_week':True},date(2026,11,15))['date_from'],'2026-11-09')
        self.assertEqual(self.store.query({'this_week':True},date(2026,11,16))['date_from'],'2026-11-16')
    def test_export_deterministic_and_contained(self):
        r=self.saved();a=self.store.brief(r['id'],True);b=self.store.brief(r['id'])
        self.assertEqual(a['markdown'],b['markdown']);self.assertEqual(Path(a['path']).read_text(),a['markdown'])
        self.assertEqual(Path(a['path']).parent,Path(self.tmp.name)/'exports')
        self.assertIn('Possibilities',a['markdown']);self.assertIn('suggestion, not an agreement',a['markdown'])
    def test_symlink_export_refused(self):
        r=self.saved()
        with tempfile.TemporaryDirectory() as outside:
            (Path(self.tmp.name)/'exports').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(Invalid):self.store.brief(r['id'],True)
    def test_duplicate_update_and_wrong_tool(self):
        r=self.saved();u=self.update(r);p=self.store.prepare('update',u)
        with self.assertRaises(Invalid):self.store.apply(p['proposal_id'],'capture')
        self.store.apply(p['proposal_id'],'update')
        self.assertEqual(self.store.prepare('update',u)['proposal_id'],p['proposal_id'])
        u['expected_revision']=2
        with self.assertRaisesRegex(Invalid,'already imported'):self.store.prepare('update',u)

    def test_timezone_at_week_boundary(self):
        from unittest.mock import patch
        from datetime import datetime, timezone
        class Fixed(datetime):
            @classmethod
            def now(cls,tz=None):
                return datetime(2026,11,16,1,0,tzinfo=timezone.utc).astimezone(tz)
        with patch('domain.datetime',Fixed):
            self.assertEqual(self.store.query({'this_week':True,'timezone':'America/New_York'})['date_from'],'2026-11-09')
            self.assertEqual(self.store.query({'this_week':True,'timezone':'UTC'})['date_from'],'2026-11-16')
    def test_duplicate_capture_different_extraction(self):
        self.saved();p=sample();p['record']['name']='Reworded name'
        proposal=self.store.prepare('capture',p)
        with self.assertRaisesRegex(Invalid,'already captured'):self.store.apply(proposal['proposal_id'],'capture')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM records').fetchone()[0],1)
    def test_schema_rejects_approval_and_payload_swap(self):
        spec=importlib.util.spec_from_file_location('cg_test',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
        module=importlib.util.module_from_spec(spec);sys.modules['cg_test']=module;spec.loader.exec_module(module)
        from cg_test.schemas import validate_arguments, SCHEMAS
        from cg_test.domain import Invalid as SchemaInvalid
        schema=SCHEMAS['common_ground_capture']['parameters']
        validate_arguments({'proposal':sample()},schema)
        for args in [{'approved':True},{'action':'approve'},{'proposal':{'source':{},'record':{}}}]:
            with self.assertRaises(SchemaInvalid):validate_arguments(args,schema)

    def test_concurrent_save_is_idempotent(self):
        from concurrent.futures import ThreadPoolExecutor
        p=self.store.prepare('capture',sample())
        def save(_):
            store=Store(sqlite3.connect(self.path,timeout=10),self.tmp.name)
            try:return store.apply(p['proposal_id'],'capture')
            finally:store.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,range(2)))
        self.assertTrue(all(x['applied'] for x in results))
        self.assertEqual(sum(bool(x.get('already_applied')) for x in results),1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM history').fetchone()[0],1)

if __name__=='__main__':unittest.main()
