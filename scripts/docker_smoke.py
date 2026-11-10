"""CI check for the Compose API and its persistent volume. Run after compose up -d."""
import json
from pathlib import Path
import subprocess
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1]

def call(method,path,data=None):
    request=urllib.request.Request('http://127.0.0.1:8080'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=3) as result:return json.load(result)

def ready():
    for _ in range(60):
        try:
            if call('GET','/health')['status']=='ok':return
        except OSError:pass
        time.sleep(.25)
    raise RuntimeError('Compose API did not become ready')

def main():
    ready()
    asset=call('POST','/assets',{'name':'CI persistence check','service':'Test','project':'CI'})
    task=call('POST','/tasks',{'title':'Verify named-volume persistence','asset_id':asset['id']})
    call('PATCH','/tasks/'+task['id'],{'status':'in_progress'})
    # Recreate rather than just restart, exercising persistence outside the container layer.
    subprocess.run(['docker','compose','up','-d','--force-recreate'],cwd=ROOT,check=True,timeout=60)
    ready()
    assert call('GET','/assets/'+asset['id'])==asset
    assert call('GET','/tasks/'+task['id'])['status']=='in_progress'
    assert call('PATCH','/tasks/'+task['id'],{'status':'done'})['status']=='done'
    print('PASS: Compose API workflow and persistent volume after container recreation')
if __name__=='__main__':main()
