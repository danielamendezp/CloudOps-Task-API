"""Read existing AWS control-plane metadata; publish only pseudonymous asset labels.
No AWS create/update/delete calls. No bucket objects, DB rows, secrets or logs read.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def alias_for(key, service, region, identity):
    digest = hmac.new(key, (service+'|'+region+'|'+identity).encode(), hashlib.sha256).hexdigest()[:16]
    return service.lower()+'-'+digest

def load_key():
    folder=ROOT/'data';folder.mkdir(exist_ok=True)
    path=folder/'inventory-alias.key'
    if not path.exists():
        try:
            with path.open('xb') as out:
                out.write(secrets.token_bytes(32))
            try:path.chmod(0o600)
            except OSError:pass
        except FileExistsError:pass
    return path.read_bytes()

def discover(session, services, region, limit):
    """Yield identifiers in memory only. Stop after limit resources per service."""
    for service in services:
        count=0
        if service=='s3':
            pages=session.client('s3',region_name=region).get_paginator('list_buckets').paginate(PaginationConfig={'PageSize':100})
            records=((bucket['Name'], 'S3') for page in pages for bucket in page.get('Buckets',[]))
        elif service=='cloudfront':
            pages=session.client('cloudfront').get_paginator('list_distributions').paginate()
            records=((item['ARN'], 'CloudFront') for page in pages for item in page.get('DistributionList',{}).get('Items',[]))
        elif service=='lightsail':
            pages=session.client('lightsail',region_name=region).get_paginator('get_instances').paginate()
            records=((item['arn'], 'Lightsail') for page in pages for item in page.get('instances',[]))
        elif service=='dynamodb':
            pages=session.client('dynamodb',region_name=region).get_paginator('list_tables').paginate()
            records=((name, 'DynamoDB') for page in pages for name in page.get('TableNames',[]))
        elif service=='lambda':
            pages=session.client('lambda',region_name=region).get_paginator('list_functions').paginate()
            records=((item['FunctionArn'], 'Lambda') for page in pages for item in page.get('Functions',[]))
        else:raise ValueError('unsupported service')
        for identity,label in records:
            yield service,label,identity
            count+=1
            if count>=limit:break

def api(method,path,data=None):
    request=urllib.request.Request('http://127.0.0.1:8080'+path,method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as result:return json.load(result)

def existing_references():
    refs=set();cursor=None
    while True:
        page=api('GET','/assets'+('?cursor='+cursor if cursor else ''))
        refs.update(x.get('reference') for x in page['items'])
        cursor=page.get('next_cursor')
        if not cursor:return refs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True,help='Existing local AWS CLI profile; use temporary credentials')
    parser.add_argument('--region',required=True,help='Region for Lightsail and DynamoDB; S3 and CloudFront are account/global listings')
    parser.add_argument('--services',nargs='+',choices=['s3','cloudfront','lightsail','dynamodb','lambda'],default=['cloudfront','lightsail','dynamodb'])
    parser.add_argument('--limit',type=int,default=50,help='Maximum resources per service, 1–100')
    parser.add_argument('--import-local',action='store_true',help='Store sanitized records in the running local API; default is preview only')
    args=parser.parse_args()
    if not 1<=args.limit<=100:parser.error('--limit must be between 1 and 100')
    try:
        import boto3
        from botocore.config import Config
        session=boto3.Session(profile_name=args.profile,region_name=args.region)
        # Apply explicit SDK timeouts and bounded retries through a wrapper.
        class Session:
            def client(self,*a,**kw):
                return session.client(*a,**kw,config=Config(connect_timeout=5,read_timeout=15,retries={'mode':'standard','total_max_attempts':2}))
        key=load_key()
        records=[]
        for service,label,identity in discover(Session(),args.services,args.region,args.limit):
            scope='global' if service in ('s3','cloudfront') else args.region
            # No raw AWS names, IDs, ARNs, account numbers, domains or IPs survive here.
            alias=alias_for(key,service,args.profile+'/'+scope,identity)
            records.append({'name':alias,'service':label,'project':'Personal AWS inventory',
                            'environment':'aws-discovered','reference':'aws-alias:'+alias})
        # Fail before imports if discovery errors; do not print provider exception bodies.
        if args.import_local:
            refs=existing_references();created=0
            for record in records:
                if record['reference'] not in refs:
                    api('POST','/assets',record);refs.add(record['reference']);created+=1
            print(json.dumps({'discovered':len(records),'created':created,'skipped_existing':len(records)-created}))
        else:
            print(json.dumps({'mode':'preview','assets':records},indent=2))
    except Exception as exc:
        # Exception strings may contain raw resource identifiers or endpoint details.
        print('Inventory failed ('+type(exc).__name__+'). Check local profile login, read-only permissions, region, SDK and API availability. No raw AWS exception was printed.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
