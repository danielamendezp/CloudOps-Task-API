"""Best-effort publication check; reports paths and categories, never secret values."""
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
    'AWS access key identifier':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'private key material':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'GitHub token':rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    'credential-bearing URL':rb'https?://[^\s/@:]+:[^\s/@]+@',
    'AWS credential assignment':rb'(?i)(?:aws_secret_access_key|aws_session_token)\s*[=:]\s*["\x27]?[A-Za-z0-9/+_=.-]{16,}'
}
def check(paths):
    findings=[]
    for path in paths:
        relative=path.relative_to(ROOT)
        if not path.is_file():continue
        if relative.parts[0] in ('data','.aws','private-exports') or path.suffix.lower() in ('.key','.pem','.p12','.pfx','.db','.tfstate','.tfplan') or path.name in ('.env','credentials','credentials.csv') or (path.name.startswith('.env.') and path.name!='.env.example'):
            findings.append((str(relative),'private runtime/configuration file'))
        if path.stat().st_size>5_000_000:continue
        data=path.read_bytes()
        for category,pattern in PATTERNS.items():
            if re.search(pattern,data):findings.append((str(relative),category))
    return findings

def main():
    try:
        result=subprocess.run(['git','-c','core.fsmonitor=false','ls-files','-z'],cwd=ROOT,capture_output=True,check=True)
        paths=[ROOT/name for name in result.stdout.decode().split('\0') if name]
        mode='Git index/tracked files'
    except (OSError,subprocess.CalledProcessError):
        paths=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('.git','.venv','.terraform','__pycache__'))]
        mode='working files (no usable Git index)'
    findings=check(paths)
    for path,category in findings:print(path+': '+category)
    print('Checked '+str(len(paths))+' '+mode+'; findings: '+str(len(findings)))
    print('This check does not inspect screenshots, full Git history, every token format, or prove that a repository contains no secrets.')
    return 1 if findings else 0
if __name__=='__main__':sys.exit(main())
