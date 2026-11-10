"""Live, read-only S3 and DynamoDB configuration report with asset aliases."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from import_aws import alias_for
from export_aws_report import local_assets

ROOT=Path(__file__).resolve().parents[1]

def read_config(call, **kwargs):
    try:
        return call(**kwargs), None
    except Exception as exc:
        code=getattr(exc,'response',{}).get('Error',{}).get('Code',type(exc).__name__)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',code):code='QueryFailed'
        return {},code

def base_record(key, profile, service, scope, identity, local):
    alias=alias_for(key,service,profile+'/'+scope,identity)
    row=local.get('aws-alias:'+alias,{})
    return {'Asset alias':alias, 'Service':service,
            'Local inventory ID':row.get('id','Not imported locally'),
            'Locally registered at':row.get('created_at','Not imported locally')}

def dynamo_record(table, base):
    result=dict(base)
    result.update({'Region':table.get('_region','Not reported'),
                   'Table status':table.get('TableStatus','Not reported'),
                   'Billing mode':table.get('BillingModeSummary',{}).get('BillingMode','Not reported'),
                   'Deletion protection enabled':table.get('DeletionProtectionEnabled','Not reported'),
                   'DynamoDB stream enabled':table.get('StreamSpecification',{}).get('StreamEnabled',False),
                   'Global secondary index count':len(table.get('GlobalSecondaryIndexes',[])),
                   'SSE status returned by API':table.get('SSEDescription',{}).get('Status','Not returned; not evidence of missing encryption')})
    return result

def collect(session, profile, region, key, local, limit):
    records=[]
    dynamo=session.client('dynamodb',region_name=region)
    count=0
    for page in dynamo.get_paginator('list_tables').paginate():
        for name in page.get('TableNames',[]):
            base=base_record(key,profile,'dynamodb',region,name,local)
            payload,error=read_config(dynamo.describe_table,TableName=name)
            if error:base['Configuration query result']=error;records.append(base)
            else:
                table=payload.get('Table',{});table['_region']=region
                records.append(dynamo_record(table,base))
            count+=1
            if count>=limit:break
        if count>=limit:break
    s3=session.client('s3',region_name=region)
    count=0
    for page in s3.get_paginator('list_buckets').paginate(PaginationConfig={'PageSize':100}):
        for bucket in page.get('Buckets',[]):
            name=bucket['Name']
            base=base_record(key,profile,'s3','global',name,local)
            location,err=read_config(s3.get_bucket_location,Bucket=name)
            bucket_region=location.get('LocationConstraint')
            if err:base['Region']='Unavailable ('+err+')';client=s3
            else:
                bucket_region={'EU':'eu-west-1',None:'us-east-1'}.get(bucket_region,bucket_region)
                base['Region']=bucket_region
                client=session.client('s3',region_name=bucket_region)
            version,error=read_config(client.get_bucket_versioning,Bucket=name)
            base['Versioning']=('Unavailable ('+error+')') if error else version.get('Status','Not enabled')
            public,error=read_config(client.get_public_access_block,Bucket=name)
            if error:
                base['Bucket-level public access block']='Not configured' if error=='NoSuchPublicAccessBlockConfiguration' else 'Unavailable ('+error+')'
            else:
                settings=public.get('PublicAccessBlockConfiguration',{})
                for flag in ('BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets'):
                    base['Bucket '+flag]=settings.get(flag,'Not returned')
            records.append(base);count+=1
            if count>=limit:break
        if count>=limit:break
    return records

def render(records):
    lines=['CloudOps Task API - Live AWS Storage Inventory',
           'Queried at: '+datetime.now(timezone.utc).isoformat(),
           'Source: live AWS control-plane queries (read-only)',
           'DynamoDB scope: selected region; S3 scope: account bucket listing',
           'Resources reported: '+str(len(records)),
           'Privacy: original table/bucket names, account IDs, ARNs, keys, rows and objects omitted.',
           'Configuration snapshot only; no data reads, changes, availability test or vulnerability scan.','']
    for record in records:
        lines.extend(str(k)+': '+str(v) for k,v in record.items());lines.append('')
    lines.extend(['Notes:',
        '- Not reported / unavailable means unknown, not a failed security control.',
        '- Bucket-level public access block does not establish effective public exposure; account settings, policies and other controls also matter.',
        '- DynamoDB SSE fields may be absent even when encryption at rest is provided.',
        '- Resources with a configuration-query error are retained with their alias and error code.',
        '- Each service is limited to the requested resource count; this is not necessarily a complete account inventory.'])
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
        path=ROOT/'data/inventory-alias.key'
        if not path.exists():raise ValueError('missing alias key')
        key=path.read_bytes()
        if len(key)!=32:raise ValueError('invalid alias key')
        local=local_assets()
        session=boto3.Session(profile_name=args.profile,region_name=args.region)
        class Session:
            def client(self,*a,**kw):
                return session.client(*a,**kw,config=Config(connect_timeout=5,read_timeout=15,retries={'mode':'standard','total_max_attempts':2}))
        records=collect(Session(),args.profile,args.region,key,local,args.limit)
        output=ROOT/'docs/evidence/aws-storage-inventory.txt'
        output.parent.mkdir(parents=True,exist_ok=True)
        temp=output.with_suffix('.tmp');temp.write_text(render(records),encoding='utf-8');temp.replace(output)
        print('Report saved: docs/evidence/aws-storage-inventory.txt ('+str(len(records))+' resources). Review before publication.')
    except Exception as exc:
        print('Storage report failed ('+type(exc).__name__+'). Check local API, alias key, AWS profile and permissions. Raw AWS errors were not printed.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
