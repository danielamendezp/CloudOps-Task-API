import json
import os
import tempfile
import unittest
import uuid
from unittest.mock import Mock, patch
from app.handler import handler
from app.storage import SQLiteStore, DynamoStore, Missing

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'LOCAL_MODE': 'true', 'DB_PATH': self.tmp.name+'/tasks.db'})
        self.env.start();self.addCleanup(self.env.stop)
    def call(self, method, path, data=None, query=''):
        r = handler({'rawPath': path, 'rawQueryString': query, 'requestContext': {'http': {'method': method}}, 'body': json.dumps(data) if data is not None else None}, None)
        return r['statusCode'], json.loads(r['body'])
    def asset(self):
        status, item = self.call('POST', '/assets', {'name': 'Personal website', 'service': 'Website', 'project': 'Personal'})
        self.assertEqual(status, 201)
        return item
    def test_asset_task_workflow(self):
        asset=self.asset()
        status,task=self.call('POST','/tasks',{'title':'Review access','asset_id':asset['id'],'priority':'high'})
        self.assertEqual(status,201)
        self.assertEqual(task['asset_id'],asset['id'])
        for state in ['in_progress','done','open']:
            status,updated=self.call('PATCH','/tasks/'+task['id'],{'status':state})
            self.assertEqual(status,200);self.assertEqual(updated['status'],state)
        self.assertEqual(self.call('GET','/assets/'+asset['id'])[1],asset)
    def test_persistent_storage(self):
        asset=self.asset()
        db=SQLiteStore(os.environ['DB_PATH'])
        self.assertEqual(db.get(asset['id'],'asset'),asset)
    def test_list_and_pagination(self):
        for _ in range(3):self.asset()
        status,page=self.call('GET','/assets',query='limit=2')
        self.assertEqual(status,200);self.assertEqual(len(page['items']),2)
        status,tail=self.call('GET','/assets',query='limit=2&cursor='+page['next_cursor'])
        self.assertEqual(len(tail['items']),1);self.assertIsNone(tail['next_cursor'])
        self.assertFalse({x['id'] for x in page['items']} & {x['id'] for x in tail['items']})
    def test_bad_titles_and_json(self):
        for title in [None,'','  ',42,'x'*121]:
            self.assertEqual(self.call('POST','/tasks',{'title':title})[0],400)
        self.assertEqual(self.call('POST','/tasks',[1])[0],400)
        r=handler({'rawPath':'/tasks','requestContext':{'http':{'method':'POST'}},'body':'{'},None)
        self.assertEqual(r['statusCode'],400)
    def test_invalid_relations(self):
        self.assertEqual(self.call('POST','/tasks',{'title':'x','asset_id':str(uuid.uuid4())})[0],404)
        self.assertEqual(self.call('POST','/tasks',{'title':'x','asset_id':'bad'})[0],400)
        task=self.call('POST','/tasks',{'title':'x'})[1]
        self.assertEqual(self.call('POST','/tasks',{'title':'x','asset_id':task['id']})[0],404)
    def test_bad_status_priority(self):
        task=self.call('POST','/tasks',{'title':'x'})[1]
        for data in [{'status':'closed'},{'status':'done','title':'changed'},{}]:
            self.assertEqual(self.call('PATCH','/tasks/'+task['id'],data)[0],400)
        self.assertEqual(self.call('POST','/tasks',{'title':'x','priority':'urgent'})[0],400)
    def test_missing_and_cross_kind_updates(self):
        asset=self.asset()
        self.assertEqual(self.call('PATCH','/tasks/'+asset['id'],{'status':'done'})[0],404)
        self.assertEqual(self.call('PATCH','/tasks/'+str(uuid.uuid4()),{'status':'done'})[0],404)
        self.assertEqual(self.call('GET','/tasks/'+asset['id'])[0],404)
    def test_health_and_routes(self):
        self.assertEqual(self.call('GET','/health')[0],200)
        self.assertEqual(self.call('GET','/other')[0],404)
        self.assertEqual(self.call('GET','/tasks/bad')[0],400)
        self.assertEqual(self.call('GET','/tasks/a/b')[0],404)
    def test_bad_query(self):
        for query in ['limit=0','limit=101','limit=bad','cursor=bad']:
            self.assertEqual(self.call('GET','/tasks',query=query)[0],400)
    def test_cloud_failure_sanitized(self):
        with patch('app.handler.get_store',side_effect=RuntimeError('private detail')), self.assertLogs('app.handler',level='ERROR'):
            status,data=self.call('GET','/assets')
        self.assertEqual(status,500);self.assertNotIn('private',json.dumps(data))
    def test_dynamo_conditional_update(self):
        db=object.__new__(DynamoStore);db.table=Mock()
        db.table.update_item.return_value={'Attributes':{'status':'done'}}
        self.assertEqual(db.update_task('id','done','now')['status'],'done')
        self.assertIn('attribute_exists',db.table.update_item.call_args.kwargs['ConditionExpression'])
        class Conditional(Exception):
            response={'Error':{'Code':'ConditionalCheckFailedException'}}
        db.table.update_item.side_effect=Conditional()
        with self.assertRaises(Missing):db.update_task('id','done','now')
    def test_dynamo_pagination(self):
        db=object.__new__(DynamoStore);db.table=Mock()
        db.table.scan.return_value={'Items':[], 'LastEvaluatedKey':{'id':'next'}}
        self.assertEqual(db.list('asset',25,'previous'),([], 'next'))
        self.assertEqual(db.table.scan.call_args.kwargs['ExclusiveStartKey'],{'id':'previous'})
    def test_large_body(self):
        self.assertEqual(self.call('POST','/tasks',{'title':'a'*17000})[0],400)

if __name__=='__main__':unittest.main()
