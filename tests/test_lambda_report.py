import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import export_lambda_report as r
import import_aws as importer
import unittest
from unittest.mock import Mock

class LambdaTests(unittest.TestCase):
    def test_sensitive_fields_removed(self):
        item={'FunctionArn':'arn:aws:lambda:us-east-1:123456789012:function:secret-name',
              'FunctionName':'secret-name','Role':'private-role','Environment':{'Variables':{'API_KEY':'secret-value'}},
              'Runtime':'python3.12','PackageType':'Zip','MemorySize':128,'Timeout':10}
        result=r.render([r.sanitize(item,b'k'*32,'default','us-east-1',{})],'us-east-1')
        for value in ['123456789012','secret-name','private-role','API_KEY','secret-value','arn:aws:']:
            self.assertNotIn(value,result)
        self.assertIn('python3.12',result)
    def test_image_runtime(self):
        item={'FunctionArn':'private-arn','PackageType':'Image'}
        self.assertEqual(r.sanitize(item,b'k'*32,'default','us-east-1',{})['Runtime'],'Not returned for image package')
    def test_discovery_alias_matches(self):
        session=Mock();session.client.return_value.get_paginator.return_value.paginate.return_value=[{'Functions':[{'FunctionArn':'private-arn'}]}]
        rows=list(importer.discover(session,['lambda'],'us-east-1',1))
        self.assertEqual(rows,[('lambda','Lambda','private-arn')])
        alias=importer.alias_for(b'k'*32,'lambda','default/us-east-1','private-arn')
        result=r.sanitize({'FunctionArn':'private-arn'},b'k'*32,'default','us-east-1',{'aws-alias:'+alias:{'id':'local-id'}})
        self.assertEqual(result['Local inventory ID'],'local-id')

if __name__=='__main__':unittest.main()
