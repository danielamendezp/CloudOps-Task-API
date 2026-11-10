"""Combine existing sanitized reports. No AWS calls; rejects incomplete inputs."""
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def combine(paths, output):
    contents=[]
    for path in paths:
        text=path.read_text(encoding='utf-8-sig')
        if not text.strip():raise ValueError('Empty input report: '+path.name)
        contents.append(text)
    text='CloudOps Task API - Consolidated AWS Inventory\nCombined at: '+datetime.now(timezone.utc).isoformat()+'\nServices: CloudFront, S3, DynamoDB, Lambda\nEach section retains its original query timestamp.\n\n'+'\n\n'.join(contents)
    temporary=output.with_suffix('.tmp')
    temporary.write_text(text,encoding='utf-8');temporary.replace(output)

def main():
    folder=ROOT/'docs/evidence'
    try:
        combine([folder/name for name in ['aws-inventory.txt','aws-storage-inventory.txt','aws-lambda-inventory.txt']],folder/'aws-inventory-report.txt')
    except (OSError,ValueError) as exc:
        print('Combination failed ('+type(exc).__name__+'). Generate all three nonempty input reports first. Existing consolidated report was preserved.')
        return 1
    print('Saved docs/evidence/aws-inventory-report.txt')
    return 0

if __name__=='__main__':raise SystemExit(main())
