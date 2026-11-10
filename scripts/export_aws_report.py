"""Live read-only CloudFront report with explicitly approved public domains."""
import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def normalize_domain(value):
    value=value.strip().lower().rstrip('.')
    if len(value)>253 or '.' not in value or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',value):
        raise ValueError('Use an exact public hostname, without URL paths or wildcards')
    if any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in value.split('.')):
        raise ValueError('Invalid hostname')
    return value

def make_record(item,key,profile,approved,local):
    identity=item['ARN']
    alias='cloudfront-'+hmac.new(key,('cloudfront|'+profile+'/global|'+identity).encode(),hashlib.sha256).hexdigest()[:16]
    domains=[]
    for domain in item.get('Aliases',{}).get('Items',[]):
        try:domain=normalize_domain(domain)
        except ValueError:continue
        if domain in approved:domains.append(domain)
    # Strict field selection: never export source objects, origins or certificate ARNs.
    record={'alias':alias,'public_domains':sorted(set(domains)),
            'status':item.get('Status','Not reported'),'enabled':item.get('Enabled','Not reported'),
            'http_version':item.get('HttpVersion','Not reported'),
            'ipv6':item.get('IsIPV6Enabled','Not reported'),
            'default_viewer_protocol':item.get('DefaultCacheBehavior',{}).get('ViewerProtocolPolicy','Not reported'),
            'tls_minimum':item.get('ViewerCertificate',{}).get('MinimumProtocolVersion','Not reported')}
    existing=local.get('aws-alias:'+alias)
    record['local_inventory_id']=existing.get('id','Not imported locally') if existing else 'Not imported locally'
    record['registered_at']=existing.get('created_at','Not imported locally') if existing else 'Not imported locally'
    return record

def render(records):
    lines=['CloudOps Task API - Live AWS CloudFront Report',
           'Queried at: '+datetime.now(timezone.utc).isoformat(),
           'Source: AWS CloudFront ListDistributions (live, read-only)',
           'Scope: CloudFront global distributions, limited to the requested result count',
           'Distributions reported: '+str(len(records)),
           'Privacy: AWS IDs, account numbers, ARNs, origins and certificate identifiers omitted.',
           'Only explicitly approved custom domains confirmed in AWS aliases are included.',
           'Configuration evidence only: not a vulnerability scan or a website availability test.','']
    for record in records:
        lines += ['Asset alias: '+record['alias'], 'Service: Amazon CloudFront',
                  'Purpose: Content delivery for personal web projects',
                  'Approved domain(s) configured in AWS: '+(', '.join(record['public_domains']) or 'Not published / no approved match'),
                  'Deployment status: '+str(record['status']), 'Distribution enabled: '+str(record['enabled']),
                  'Supported HTTP setting: '+str(record['http_version']), 'IPv6 enabled: '+str(record['ipv6']),
                  'Default cache behavior viewer protocol: '+str(record['default_viewer_protocol']),
                  'Viewer certificate minimum TLS setting: '+str(record['tls_minimum']),
                  'Local inventory ID: '+record['local_inventory_id'], 'Locally registered at: '+record['registered_at'],'']
    lines += ['Notes:', '- Configured domain aliases do not prove DNS currently points to this distribution.',
              '- Deployed and enabled do not prove the website responds successfully.',
              '- The viewer protocol field describes the DEFAULT behavior; other behaviors may differ.',
              '- Resources not imported locally are reported without a local inventory ID.']
    return '\n'.join(lines)+'\n'

def local_assets():
    records={};cursor=None
    while True:
        url='http://127.0.0.1:8080/assets?limit=100'+('&cursor='+cursor if cursor else '')
        with urllib.request.urlopen(url,timeout=10) as result:page=json.load(result)
        for item in page['items']:
            if item.get('environment')=='aws-discovered':records[item.get('reference')]=item
        cursor=page.get('next_cursor')
        if not cursor:return records

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--region',default='us-east-1',help='SDK region; CloudFront inventory is global')
    parser.add_argument('--public-domains',nargs='+',required=True,help='Exact public hostnames you approve for publication')
    parser.add_argument('--limit',type=int,default=50)
    args=parser.parse_args()
    if not 1<=args.limit<=100:parser.error('--limit must be 1–100')
    try:approved={normalize_domain(x) for x in args.public_domains}
    except ValueError as exc:parser.error(str(exc))
    try:
        import boto3
        from botocore.config import Config
        key_path=ROOT/'data/inventory-alias.key'
        if not key_path.exists():
            print('Missing local alias key. Run the inventory importer from this same project folder first.',file=sys.stderr)
            return 1
        key=key_path.read_bytes()
        if len(key)!=32:raise ValueError('Invalid alias key length')
        local=local_assets()
        client=boto3.Session(profile_name=args.profile,region_name=args.region).client('cloudfront',config=Config(connect_timeout=5,read_timeout=15,retries={'mode':'standard','total_max_attempts':2}))
        records=[]
        for page in client.get_paginator('list_distributions').paginate():
            for item in page.get('DistributionList',{}).get('Items',[]):
                records.append(make_record(item,key,args.profile,approved,local))
                if len(records)>=args.limit:break
            if len(records)>=args.limit:break
        output=ROOT/'docs/evidence/aws-inventory.txt'
        output.parent.mkdir(parents=True,exist_ok=True)
        temporary=output.with_suffix('.tmp')
        temporary.write_text(render(records),encoding='utf-8')
        temporary.replace(output)
        print('Report saved: docs/evidence/aws-inventory.txt ('+str(len(records))+' distributions). Review before publication.')
    except Exception as exc:
        print('Report failed ('+type(exc).__name__+'). Check AWS profile permissions, running local API and alias key. Existing TXT was not overwritten by a partial AWS response.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
