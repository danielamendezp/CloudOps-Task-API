import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import export_storage_report as r
import unittest
from unittest.mock import Mock

class StorageTests(unittest.TestCase):
    def test_no_private_names_or_arns(self):
        base=r.base_record(b'k'*32,'default','dynamodb','us-east-1','secret-table',{})
        record=r.dynamo_record({'TableName':'secret-table','TableArn':'secret-arn','TableStatus':'ACTIVE','KeySchema':[{'AttributeName':'private-field'}]},base)
        result=r.render([record])
        for secret in ['secret-table','secret-arn','private-field']:self.assertNotIn(secret,result)
        self.assertIn('ACTIVE',result)
    def test_errors_are_not_raw(self):
        class Failure(Exception):response={'Error':{'Code':'AccessDenied','Message':'secret-bucket'}}
        method=Mock(side_effect=Failure())
        value,error=r.read_config(method)
        self.assertEqual(value,{});self.assertEqual(error,'AccessDenied')
    def test_s3_region_and_errors(self):
        dynamo=Mock();dynamo.get_paginator.return_value.paginate.return_value=[{'TableNames':[]}]
        s3=Mock();s3.get_paginator.return_value.paginate.return_value=[{'Buckets':[{'Name':'private-bucket'}]}]
        s3.get_bucket_location.return_value={'LocationConstraint':None}
        s3.get_bucket_versioning.return_value={}
        class Missing(Exception):response={'Error':{'Code':'NoSuchPublicAccessBlockConfiguration'}}
        s3.get_public_access_block.side_effect=Missing()
        session=Mock();session.client.side_effect=lambda name,**kwargs:dynamo if name=='dynamodb' else s3
        records=r.collect(session,'default','us-east-1',b'k'*32,{},1)
        self.assertEqual(records[0]['Region'],'us-east-1')
        self.assertEqual(records[0]['Bucket-level public access block'],'Not configured')
        self.assertNotIn('private-bucket',r.render(records))

if __name__=='__main__':unittest.main()
