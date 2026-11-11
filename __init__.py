"""Common Ground native Hermes plugin."""
import json
from pathlib import Path
from .domain import Store, Invalid, exact_keys, require
from .schemas import SCHEMAS, validate_arguments

def register(ctx):
    # Resolve storage for every call: profiles must never share a cached connection.
    def handler_for(name):
        def handler(args, **kwargs):
            db=None
            try:
                from plugins.plugin_storage import plugin_data_dir, plugin_db
                validate_arguments(args,SCHEMAS[name]['parameters'])
                db=plugin_db('common-ground'); store=Store(db,plugin_data_dir('common-ground'))
                kind=name.removeprefix('common_ground_')
                if kind in ['capture','update']:
                    action=args.get('action','prepare')
                    if action=='prepare':
                        require('proposal' in args and 'proposal_id' not in args,'prepare requires proposal only')
                        result=store.prepare(kind,args['proposal'])
                    elif action in ['preview','apply']:
                        require('proposal_id' in args and 'proposal' not in args,'preview/apply accepts only the stored proposal_id')
                        result=store.preview(args['proposal_id']) if action=='preview' else store.apply(args['proposal_id'],kind)
                    else: raise Invalid('action must be prepare, preview or apply')
                elif kind=='query':
                    result=store.query(dict(args,timezone=args.get('timezone') or ctx.get_config('timezone','UTC')))
                else: result=store.brief(args['collaboration_id'],args.get('export',False))
                return json.dumps({'ok':True,**result},ensure_ascii=False)
            except (ValueError,KeyError,TypeError,AttributeError) as exc:
                return json.dumps({'ok':False,'error':str(exc),'next_step':'Correct the arguments or retrieve the current record and prepare a new proposal. No record changes were applied.'})
            except Exception as exc:
                return json.dumps({'ok':False,'error':f'{type(exc).__name__}: {exc}'})
            finally:
                if db is not None: db.close()
        return handler
    for name,schema in SCHEMAS.items():
        ctx.register_tool(name=name,toolset='common_ground',schema=schema,handler=handler_for(name))
    ctx.register_skill(name='workflow',path=Path(__file__).parent/'skills'/'workflow'/'SKILL.md',description='Capture, review and track collaborations with source evidence and explicit approval.')
