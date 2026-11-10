import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('report',Path(__file__).resolve().parents[1]/'scripts/export_aws_report.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class ReportTests(unittest.TestCase):
    def sample(self):
        return {'ARN':'arn:aws:cloudfront::123456789012:distribution/SECRET-ID',
                'DomainName':'private.cloudfront.net','Origins':{'Items':[{'DomainName':'private-origin.s3.amazonaws.com'}]},
                'Aliases':{'Items':['daniwebworks.com','private.example.com']},'Enabled':True,'Status':'Deployed',
                'HttpVersion':'http2','IsIPV6Enabled':True,'DefaultCacheBehavior':{'ViewerProtocolPolicy':'redirect-to-https'},
                'ViewerCertificate':{'ACMCertificateArn':'private-certificate','MinimumProtocolVersion':'TLSv1.2_2021'}}
    def test_safe_fields_and_domain_allowlist(self):
        record=r.make_record(self.sample(),b'k'*32,'default',{'daniwebworks.com'}, {})
        output=r.render([record])
        self.assertIn('daniwebworks.com',output)
        for secret in ['123456789012','SECRET-ID','private.example.com','private-origin','private.cloudfront.net','private-certificate','arn:aws:']:
            self.assertNotIn(secret,output)
        self.assertIn('redirect-to-https',output)
    def test_match_same_importer_alias(self):
        from test_importer import module
        expected=module.alias_for(b'k'*32,'cloudfront','default/global',self.sample()['ARN'])
        record=r.make_record(self.sample(),b'k'*32,'default',set(),{'aws-alias:'+expected:{'id':'local-uuid','created_at':'local-time'}})
        self.assertEqual(record['alias'],expected)
        self.assertEqual(record['local_inventory_id'],'local-uuid')
        self.assertEqual(record['public_domains'],[])
    def test_domain_validation(self):
        self.assertEqual(r.normalize_domain('DaniWebWorks.COM.'),'daniwebworks.com')
        for bad in ['https://daniwebworks.com','*.example.com','example.com/path','example..com','-a.example.com']:
            with self.assertRaises(ValueError):r.normalize_domain(bad)

if __name__=='__main__':unittest.main()
