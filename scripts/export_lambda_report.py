"""Live Lambda inventory; exports only selected metadata, never invokes functions."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from import_aws import alias_for
from export_aws_report import local_assets

ROOT=Path(__file__).resolve().parents[1]

def sanitize(item,key,profile,region,local):
    alias=alias_for(key,'lambda',profile+'/'+region,item['FunctionArn'])
    row=local.get('aws-alias:'+alias,{})
    package=item.get('PackageType','Not reported')
    return {'Asset alias':alias,'Service':'AWS Lambda','Region':region,
            'Package type':package,
            'Runtime':item.get('Runtime','Not returned for image package' if package=='Image' else 'Not reported'),
            'Architecture':', '.join(item.get('Architectures',[])) or 'Not reported',
            'Memory (MB)':item.get('MemorySize','Not reported'),
            'Timeout (seconds)':item.get('Timeout','Not reported'),
            'Ephemeral storage (MB)':item.get('EphemeralStorage',{}).get('Size','Not reported'),
            'Last modified (AWS)':item.get('LastModified','Not reported'),
            'Local inventory ID':row.get('id','Not imported locally'),
            'Locally registered at':row.get('created_at','Not imported locally')}

def render(records,region):
    lines=['CloudOps Task API - Live AWS Lambda Report',
           'Queried at: '+datetime.now(timezone.utc).isoformat(),
           'Source: AWS Lambda ListFunctions (live, read-only)',
           'Region: '+region, 'Functions reported: '+str(len(records)),
           'Privacy: original function names, ARNs, roles, environment variables and code identifiers omitted.',
           'Configuration snapshot only. No functions invoked, code downloaded, or configurations changed.','']
    for record in records:
        lines.extend(str(k)+': '+str(v) for k,v in record.items());lines.append('')
    lines += ['Notes:', '- ListFunctions does not establish runtime health or report the complete deployment state.',
              '- Memory, timeout and storage are configuration settings, not measured usage or estimated cost.',
              '- This report is limited to the requested resource count in one region.',
              '- No published version enumeration or vulnerability assessment is performed.']
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--region',required=True)
    parser.add_argument('--limit',type=int,default=10)
    args=parser.parse_args()
    if not 1<=args.limit<=100:parser.error('--limit must be between 1 and 100')
    try:
        import boto3
        from botocore.config import Config
        key=(ROOT/'data/inventory-alias.key').read_bytes()
        if len(key)!=32:raise ValueError('invalid alias key')
        local=local_assets()
        client=boto3.Session(profile_name=args.profile,region_name=args.region).client('lambda',config=Config(connect_timeout=5,read_timeout=15,retries={'mode':'standard','total_max_attempts':2}))
        records=[]
        for page in client.get_paginator('list_functions').paginate():
            for item in page.get('Functions',[]):
                records.append(sanitize(item,key,args.profile,args.region,local))
                if len(records)>=args.limit:break
            if len(records)>=args.limit:break
        output=ROOT/'docs/evidence/aws-lambda-inventory.txt'
        output.parent.mkdir(parents=True,exist_ok=True)
        temporary=output.with_suffix('.tmp');temporary.write_text(render(records,args.region),encoding='utf-8');temporary.replace(output)
        print('Report saved: docs/evidence/aws-lambda-inventory.txt ('+str(len(records))+' functions). Review before publication.')
    except Exception as exc:
        print('Lambda report failed ('+type(exc).__name__+'). Check local API, alias key, profile and lambda:ListFunctions permissions. Raw AWS errors were not printed.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
