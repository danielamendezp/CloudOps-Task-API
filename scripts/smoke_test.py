"""Real local HTTP integration test with restart; no AWS or remote calls."""
import json, os, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]

def main():
    lines=['# Local HTTP integration evidence','','Executed: '+datetime.now(timezone.utc).isoformat(),'',
           'Environment: Python + temporary SQLite database. No AWS deployment, Docker execution or external website check.','']
    with tempfile.TemporaryDirectory() as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        env=dict(os.environ,LOCAL_MODE='true',DB_PATH=temp+'/cloudops.db',PORT=str(port),BIND_HOST='127.0.0.1')
        def call(method,path,data=None):
            req=urllib.request.Request(base+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=5) as result:return json.load(result)
        def start():
            p=subprocess.Popen([sys.executable,'-m','app.local'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for _ in range(100):
                if p.poll() is not None:raise RuntimeError('server exited')
                try:call('GET','/health');return p
                except (OSError,urllib.error.URLError):time.sleep(.05)
            p.terminate();p.wait();raise RuntimeError('server startup timed out')
        p=start()
        try:
            asset=call('POST','/assets',{'name':'Dani WebWorks public website','service':'Website','project':'Dani WebWorks','reference':'https://daniwebworks.com','environment':'personal-business'})
            lines+=['## Manually registered real-world asset','','```json',json.dumps(asset,indent=2),'```','']
            pending=call('POST','/tasks',{'title':'Review website availability and document the result','asset_id':asset['id']})
            task=call('POST','/tasks',{'title':'Verify asset inventory survives a local process restart','asset_id':asset['id']})
            assert call('PATCH','/tasks/'+task['id'],{'status':'in_progress'})['status']=='in_progress'
            assert call('GET','/assets')['items']==[asset]
            page=call('GET','/tasks?limit=1');assert page['next_cursor']
            assert len(call('GET','/tasks?limit=1&cursor='+page['next_cursor'])['items'])==1
            p.terminate();p.wait();p=start()
            assert call('GET','/assets/'+asset['id'])==asset
            assert call('GET','/tasks/'+task['id'])['status']=='in_progress'
            done=call('PATCH','/tasks/'+task['id'],{'status':'done'});assert done['status']=='done'
            assert call('GET','/tasks/'+pending['id'])['status']=='open'
            lines+=['## Completed application verification','','```json',json.dumps(done,indent=2),'```','',
                    'PASS: health, asset registration, linked task creation, list pagination, status updates, persistence across process restart.','',
                    'The website availability task remains OPEN. No availability or security inspection of the website was performed.','',
                    'This temporary test database was removed after verification. Run try_real_asset.ps1 against your running instance to keep your own records.']
        finally:p.terminate();p.wait()
    print('\n'.join(lines))
    if '--record' in sys.argv:(ROOT/'docs/local-integration-evidence.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
