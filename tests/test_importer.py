import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock
spec=importlib.util.spec_from_file_location('aws_importer',Path(__file__).resolve().parents[1]/'scripts/import_aws.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ImportTests(unittest.TestCase):
    def test_pseudonym_stable_and_keyed(self):
        a=module.alias_for(b'private-key','cloudfront','global','arn:aws:cloudfront::123456789012:distribution/PRIVATE')
        self.assertEqual(a,module.alias_for(b'private-key','cloudfront','global','arn:aws:cloudfront::123456789012:distribution/PRIVATE'))
        self.assertNotEqual(a,module.alias_for(b'other-key','cloudfront','global','arn:aws:cloudfront::123456789012:distribution/PRIVATE'))
        self.assertNotIn('123456789012',a);self.assertNotIn('PRIVATE',a)
    def test_services_and_limits(self):
        session=Mock()
        session.client.return_value.get_paginator.return_value.paginate.return_value=[{'TableNames':['table-a','table-b']}]
        rows=list(module.discover(session,['dynamodb'],'us-east-1',1))
        self.assertEqual(rows,[('dynamodb','DynamoDB','table-a')])
        session.client.return_value.get_paginator.assert_called_once_with('list_tables')
    def test_global_page_shape(self):
        session=Mock()
        session.client.return_value.get_paginator.return_value.paginate.return_value=[{'DistributionList':{'Items':[{'ARN':'private-arn'}]}}]
        self.assertEqual(list(module.discover(session,['cloudfront'],'us-east-1',5)),[('cloudfront','CloudFront','private-arn')])
    def test_s3_and_lightsail_shapes(self):
        for service,page,expected in [('s3',{'Buckets':[{'Name':'private-bucket'}]},'private-bucket'),('lightsail',{'instances':[{'arn':'private-arn'}]},'private-arn')]:
            session=Mock();session.client.return_value.get_paginator.return_value.paginate.return_value=[page]
            self.assertEqual(list(module.discover(session,[service],'us-east-1',5))[0][2],expected)

if __name__=='__main__':unittest.main()
