"""Validated, transactional collaboration records. Standard library only."""
from __future__ import annotations
import copy
import hashlib
import json
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def uid(): return uuid.uuid4().hex

def now(): return datetime.now(timezone.utc).isoformat()

def encoded(value): return json.dumps(value, sort_keys=True, ensure_ascii=False)

class Invalid(ValueError): pass

def require(condition, message):
    if not condition: raise Invalid(message)

def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label} must be nonempty text')
    return value

def strict_date(value):
    if value is None: return None
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'Use YYYY-MM-DD or null for dates')
    try: return date.fromisoformat(value)
    except ValueError: raise Invalid(f'Invalid calendar date: {value}')

def exact_keys(obj, allowed, label):
    require(isinstance(obj, dict), f'{label} must be an object')
    require(not set(obj) - set(allowed), f'Unknown {label} fields: {set(obj)-set(allowed)}')

def evidence(items, sources, required=True):
    require(isinstance(items, list), 'evidence must be an array')
    require(not required or items, 'Supporting evidence is required')
    for item in items:
        exact_keys(item, ['source_id','quote','start','end'], 'evidence')
        require(item.get('source_id') in sources, 'Unknown source_id in evidence')
        quote = text(item.get('quote'), 'Evidence quote')
        original = sources[item['source_id']]['text']
        require(quote in original, 'Evidence quote does not occur in source text')
        if 'start' in item or 'end' in item:
            a,b = item.get('start'),item.get('end')
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(original), 'Invalid evidence character offsets')
            require(original[a:b] == quote, 'Evidence offsets do not match quote (Python Unicode characters)')

def validate(record):
    exact_keys(record, ['id','revision','name','counterpart','contact','shared_goal','goal_evidence','contributions','stage','open_questions','discrepancies','sources','commitments','created_at','updated_at'], 'collaboration')
    for key in ['name','counterpart','shared_goal']: text(record.get(key), key)
    require(record.get('contact') is None or isinstance(record['contact'], str), 'contact must be text or null')
    require(record.get('stage') in ['exploring','scoping','active','paused','closed'], 'Invalid collaboration stage')
    require(isinstance(record.get('open_questions'), list) and all(isinstance(x,str) for x in record['open_questions']), 'open_questions must be strings')
    require(isinstance(record.get('sources'), list), 'sources must be an array')
    sources = {}
    for source in record['sources']:
        exact_keys(source, ['id','title','text','url','source_date','added_at'], 'source')
        require(source['id'] not in sources, 'Duplicate source ID')
        text(source['title'], 'Source title'); text(source['text'], 'Source text')
        strict_date(source.get('source_date'))
        require(source.get('url') is None or isinstance(source['url'],str), 'Source URL must be text or null')
        sources[source['id']] = source
    evidence(record.get('goal_evidence'), sources)
    require(isinstance(record.get('contributions'), list), 'contributions must be an array')
    for contribution in record['contributions']:
        exact_keys(contribution, ['side','text','status','evidence'], 'contribution')
        text(contribution.get('text'), 'Contribution')
        require(contribution.get('side') in ['ours','theirs','unresolved'], 'Invalid contribution side')
        require(contribution.get('status') in ['proposed','source-supported','unknown'], 'Invalid contribution status')
        evidence(contribution.get('evidence',[]),sources, contribution['status'] != 'unknown')
    require(isinstance(record.get('commitments'),list), 'commitments must be an array')
    ids=set()
    for c in record['commitments']:
        exact_keys(c, ['id','action','owner','side','due_date','date_wording','status','evidence','update_evidence'], 'commitment')
        require(c['id'] not in ids, 'Duplicate commitment ID'); ids.add(c['id'])
        text(c.get('action'), 'Commitment action')
        require(c.get('owner') is None or isinstance(c['owner'],str) and bool(c['owner'].strip()), 'Owner must be nonempty text or null')
        require(c.get('side') in ['ours','theirs','unresolved'], 'Invalid owner side')
        require(c.get('status') in ['proposed','agreed','completed','cancelled'], 'Invalid commitment status')
        strict_date(c.get('due_date'))
        require(c.get('date_wording') is None or isinstance(c['date_wording'],str), 'date_wording must be text or null')
        evidence(c.get('evidence'), sources)
        evidence(c.get('update_evidence',[]),sources,False)
    require(isinstance(record.get('discrepancies'), list), 'discrepancies must be an array')
    for d in record['discrepancies']:
        require(d['commitment_id'] in ids and d['status'] in ['unresolved','resolved'], 'Invalid discrepancy')
        evidence(d['evidence'],sources)

class Store:
    def __init__(self, connection, data_dir):
        self.db=connection; self.db.row_factory=sqlite3.Row
        self.data_dir=Path(data_dir)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, record_id TEXT NOT NULL, expected INTEGER NOT NULL, body TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, applied INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, record_id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, UNIQUE(record_id, revision));
        PRAGMA user_version=1;
        ''')

    def get(self, identifier):
        row=self.db.execute('SELECT body FROM records WHERE id=?',(identifier,)).fetchone()
        require(row is not None, 'Collaboration not found')
        return json.loads(row[0])

    def source(self, raw):
        exact_keys(raw,['title','text','url','source_date'],'source')
        return dict(raw,id=uid(),added_at=now())

    def prepare(self, kind, args):
        """Only proposals are written here. Durable records change only in apply."""
        exact_keys(args, ['source','record','collaboration_id','expected_revision','changes','commitment_changes','new_commitments','resolve','reason'], 'proposal request')
        fingerprint=hashlib.sha256(encoded([kind,args]).encode()).hexdigest()
        old=self.db.execute('SELECT id,body,applied FROM proposals WHERE fingerprint=?',(fingerprint,)).fetchone()
        if old: return self.preview(old['id'])
        source=self.source(args['source'])
        if kind=='capture':
            r=copy.deepcopy(args['record'])
            exact_keys(r,['name','counterpart','contact','shared_goal','goal_evidence','contributions','stage','open_questions','commitments'],'new collaboration')
            r.update(id=uid(),revision=1,created_at=now(),updated_at=now(),sources=[source],discrepancies=[])
            r.setdefault('contact',None); r.setdefault('stage','exploring'); r.setdefault('open_questions',[]);r.setdefault('contributions',[]);r.setdefault('commitments',[])
            for c in r['commitments']: c['id']=uid()
            expected=0
        else:
            r=self.get(args['collaboration_id']); expected=args['expected_revision']
            require(type(expected) is int and expected==r['revision'],'Stale revision; query current record and prepare again')
            require(not any(s['text']==source['text'] and s.get('source_date')==source.get('source_date') for s in r['sources']), 'This source was already imported; query existing record')
            r['sources'].append(source)
            changes=args.get('changes',{})
            exact_keys(changes,['name','counterpart','contact','shared_goal','goal_evidence','contributions','stage','open_questions'],'changes')
            if 'shared_goal' in changes: require('goal_evidence' in changes,'A changed goal needs new evidence')
            r.update(copy.deepcopy(changes))
            lookup={c['id']:c for c in r['commitments']}
            seen=set()
            for patch in args.get('commitment_changes',[]):
                exact_keys(patch,['id','action','owner','side','due_date','date_wording','status','evidence'],'commitment change')
                cid=patch['id'];require(cid in lookup and cid not in seen,'Unknown or repeated commitment ID');seen.add(cid)
                c=lookup[cid]; ev=copy.deepcopy(patch.get('evidence',[]));require(ev,'Changes need evidence')
                delta={k:v for k,v in patch.items() if k not in ['id','evidence'] and c.get(k)!=v}
                protected=c['status'] in ['agreed','completed','cancelled'] and any(k in delta for k in ['due_date','owner','side','action'])
                protected=protected or 'status' in delta and (c['status'] in ['completed','cancelled'] or delta['status']=='proposed')
                if protected:
                    r['discrepancies'].append(dict(id=uid(),commitment_id=cid,status='unresolved',before={k:c.get(k) for k in delta},proposed=delta,evidence=ev))
                else: c.update(delta); c['update_evidence']=c.get('update_evidence',[])+ev
            for raw in args.get('new_commitments',[]):
                c=copy.deepcopy(raw);require('id' not in c,'New commitments cannot supply IDs');c['id']=uid();r['commitments'].append(c)
            for resolution in args.get('resolve',[]):
                exact_keys(resolution,['id','decision','evidence'],'resolution')
                d=next((x for x in r['discrepancies'] if x['id']==resolution['id']),None)
                require(d is not None and d['status']=='unresolved','Unknown or already resolved discrepancy')
                require(resolution['decision'] in ['keep','accept'],'Resolution must keep or accept')
                ev=resolution.get('evidence',[]); require(ev,'Resolution requires supplied clarification evidence')
                if resolution['decision']=='accept':
                    c=lookup[d['commitment_id']]
                    require(all(c.get(k)==v for k,v in d['before'].items()),'Agreement changed since discrepancy; clarify again')
                    c.update(d['proposed']);c['update_evidence']=c.get('update_evidence',[])+ev
                d.update(status='resolved',decision=resolution['decision'],resolution_evidence=ev)
            r['revision']+=1;r['updated_at']=now()
        # "new" always refers to the source supplied in this request.
        def bind(obj):
            if isinstance(obj,dict):
                if obj.get('source_id')=='new': obj['source_id']=source['id']
                for v in obj.values(): bind(v)
            elif isinstance(obj,list):
                for v in obj: bind(v)
        bind(r);validate(r)
        sources={s['id']:s for s in r['sources']}
        for d in r['discrepancies']:
            if 'resolution_evidence' in d: evidence(d['resolution_evidence'],sources)
            # Validate proposed values before allowing a conflict to be saved.
            trial=copy.deepcopy(r)
            next(c for c in trial['commitments'] if c['id']==d['commitment_id']).update(d['proposed'])
            validate(trial)
        pid=uid();reason=text(args.get('reason','Capture supplied note' if kind=='capture' else 'Update from supplied note'),'reason')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO proposals VALUES(?,?,?,?,?,?,?,?,0)',(pid,fingerprint,kind,r['id'],expected,encoded(r),reason,now()))
        pid=self.db.execute('SELECT id FROM proposals WHERE fingerprint=?',(fingerprint,)).fetchone()[0]
        return self.preview(pid)

    def preview(self,pid):
        p=self.db.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone();require(p is not None,'Proposal not found')
        after=json.loads(p['body'])
        before=None if p['expected']==0 else self.get(p['record_id'])
        return dict(proposal_id=pid,applied=bool(p['applied']),expected_revision=p['expected'],record=after,changes={k:{'before':None if before is None else before.get(k),'after':v} for k,v in after.items() if before is None or before.get(k)!=v},review='Show the proposed changes, evidence and unresolved questions. Obtain explicit user approval before apply. Saving does not establish external agreement.')

    def apply(self,pid,kind):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            p=self.db.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone();require(p is not None,'Proposal not found')
            require(p['kind']==kind,'Proposal belongs to the other tool')
            if p['applied']:
                self.db.rollback();return dict(applied=True,already_applied=True,collaboration_id=p['record_id'],revision=p['expected']+1)
            row=self.db.execute('SELECT revision,body FROM records WHERE id=?',(p['record_id'],)).fetchone()
            require((row['revision'] if row else 0)==p['expected'],'Stale proposal; query and prepare again')
            before=json.loads(row['body']) if row else None; after=json.loads(p['body']);validate(after)
            if kind=='capture':
                for existing in self.db.execute('SELECT body FROM records'):
                    other=json.loads(existing[0])
                    same_party=other['counterpart'].casefold().strip()==after['counterpart'].casefold().strip()
                    same_source=any(s['text']==after['sources'][0]['text'] and s.get('source_date')==after['sources'][0].get('source_date') for s in other['sources'])
                    require(not(same_party and same_source),'Source already captured for this counterpart; query existing collaboration')
            self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)',(after['id'],after['revision'],p['body']))
            entry=dict(timestamp=now(),entity=after['id'],revision=after['revision'],reason=p['reason'],source_id=after['sources'][-1]['id'],changes={k:{'before':None if before is None else before.get(k),'after':v} for k,v in after.items() if before is None or before.get(k)!=v})
            self.db.execute('INSERT INTO history(record_id,revision,body) VALUES(?,?,?)',(after['id'],after['revision'],encoded(entry)))
            self.db.execute('UPDATE proposals SET applied=1 WHERE id=?',(pid,));self.db.commit()
            return dict(applied=True,collaboration_id=after['id'],revision=after['revision'])
        except Exception: self.db.rollback();raise

    def query(self,args,today=None):
        if args.get('collaboration_id'):
            r=self.get(args['collaboration_id'])
            return dict(record=r,history=[json.loads(x[0]) for x in self.db.execute('SELECT body FROM history WHERE record_id=? ORDER BY revision',(r['id'],))])
        tz=args.get('timezone','UTC');today=today or datetime.now(ZoneInfo(tz)).date()
        start=strict_date(args.get('date_from'));end=strict_date(args.get('date_to'))
        if args.get('this_week'): start=today-timedelta(days=today.weekday());end=start+timedelta(days=6)
        require(not(start and end) or start<=end,'date_from must precede date_to')
        result=dict(timezone=tz,today=today.isoformat(),date_from=start.isoformat() if start else None,date_to=end.isoformat() if end else None,collaborations=[],overdue=[],upcoming=[],undated=[],proposed=[],completed=[],cancelled=[])
        for row in self.db.execute('SELECT body FROM records ORDER BY id'):
            r=json.loads(row[0])
            if args.get('search','').casefold() not in (r['name']+' '+r['counterpart']+' '+r['shared_goal']).casefold(): continue
            result['collaborations'].append({k:r[k] for k in ['id','revision','name','stage']})
            for c in r['commitments']:
                if any(args.get(k) and c[k]!=args[k] for k in ['side','owner','status']): continue
                item=dict(c,collaboration_id=r['id'],collaboration_name=r['name'])
                if c['status'] in ['proposed','completed','cancelled']: result[c['status']].append(item);continue
                due=strict_date(c.get('due_date'))
                if due is None: result['undated'].append(item)
                elif due<today: result['overdue'].append(item)
                elif (not start or due>=start) and (not end or due<=end): result['upcoming'].append(item)
        for key in ['overdue','upcoming','undated','proposed','completed','cancelled']: result[key].sort(key=lambda c:(c.get('due_date') or '9999-12-31',c['id']))
        return result

    def brief(self,cid,export=False):
        r=self.get(cid)
        def clean(value): return str(value).replace('\n',' ').replace('\r',' ').replace('<','&lt;').replace('>','&gt;')
        lines=[f"# {clean(r['name'])}",f"Collaboration: {r['id']} · revision {r['revision']}",f"Counterpart: {clean(r['counterpart'])} · stage: {r['stage']}",'','## Shared goal',clean(r['shared_goal']),'','## Contributions']
        for c in r['contributions']: lines.append(f"- {c['side']} · {c['status']}: {clean(c['text'])}")
        for title,statuses in [('Commitments',['agreed','completed','cancelled']),('Possibilities',['proposed'])]:
            lines+=['',f'## {title}']
            for c in r['commitments']:
                if c['status'] in statuses: lines.append(f"- [{c['status']}] {clean(c['action'])} — {clean(c.get('owner') or 'Owner unresolved')} ({c['side']}), due {c.get('due_date') or 'unresolved'}. ID: {c['id']}. Sources: {', '.join(dict.fromkeys(e['source_id'] for e in c['evidence']+c.get('update_evidence',[])))}")
        lines+=['','## Open questions']+['- '+clean(q) for q in r['open_questions']]
        lines+=['','## Discrepancies']
        for d in r['discrepancies']:
            changes=[]
            for field, value in d['proposed'].items():
                if field=='date_wording' and 'due_date' in d['proposed']: continue
                label={'due_date':'Deadline','owner':'Owner','side':'Side','action':'Action','status':'Status','date_wording':'Date wording'}.get(field,field)
                changes.append(f"{label}: {clean(d['before'].get(field) or 'unknown')} → {clean(value or 'unknown')}")
            decision={'accept':'; proposed change accepted','keep':'; original agreement kept'}.get(d.get('decision'),'')
            lines.append(f"- {d['status'].capitalize()}{decision}: {'; '.join(changes)}. Reference: {d['id']}")
        lines+=['','## Suggested next step','Clarify unresolved owners, dates and discrepancies; then review the next outstanding agreed commitment. This is a suggestion, not an agreement.','','## Source evidence']
        for s in r['sources']: lines += [f"### {clean(s['title'])} ({s['id']})",f"Source date: {s.get('source_date') or 'unknown'}; imported: {s['added_at']}",*(['URL: '+clean(s['url'])] if s.get('url') else []),'> '+clean(s['text'])]
        markdown='\n'.join(lines)+'\n';result={'markdown':markdown}
        if export:
            folder=self.data_dir/'exports';folder.mkdir(exist_ok=True,parents=True)
            require(not folder.is_symlink() and folder.resolve().parent==self.data_dir.resolve(),'Unsafe export directory')
            path=folder/f'brief-{uid()}.md'
            with path.open('x',encoding='utf-8') as f:f.write(markdown)
            result['path']=str(path)
        return result
