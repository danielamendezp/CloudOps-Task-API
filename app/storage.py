"""SQLite for local use; DynamoDB for AWS. No credentials are stored in records."""
import json
import os
import sqlite3
from pathlib import Path

class Missing(Exception):
    pass

class SQLiteStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL)")
    def connect(self):
        return sqlite3.connect(self.path, timeout=10)
    def put(self, item):
        with self.connect() as db:
            db.execute("INSERT INTO records VALUES (?, ?, ?)", (item['id'], item['kind'], json.dumps(item)))
    def get(self, key, kind):
        with self.connect() as db:
            row = db.execute("SELECT body FROM records WHERE id=? AND kind=?", (key, kind)).fetchone()
        return json.loads(row[0]) if row else None
    def list(self, kind, limit, cursor=None):
        with self.connect() as db:
            rows = db.execute("SELECT id, body FROM records WHERE kind=? AND id>? ORDER BY id LIMIT ?", (kind, cursor or '', limit+1)).fetchall()
        return [json.loads(row[1]) for row in rows[:limit]], rows[limit-1][0] if len(rows)>limit else None
    def update_task(self, key, status, updated_at):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM records WHERE id=? AND kind='task'", (key,)).fetchone()
            if not row:
                raise Missing()
            item = json.loads(row[0])
            item.update(status=status, updated_at=updated_at)
            db.execute("UPDATE records SET body=? WHERE id=?", (json.dumps(item), key))
        return item

class DynamoStore:
    def __init__(self):
        import boto3
        self.table = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
    def put(self, item):
        self.table.put_item(Item=item, ConditionExpression='attribute_not_exists(id)')
    def get(self, key, kind):
        item = self.table.get_item(Key={'id': key}, ConsistentRead=True).get('Item')
        return item if item and item.get('kind') == kind else None
    def list(self, kind, limit, cursor=None):
        args = {'Limit': limit, 'FilterExpression': '#k = :k',
                'ExpressionAttributeNames': {'#k': 'kind'}, 'ExpressionAttributeValues': {':k': kind}}
        if cursor:
            args['ExclusiveStartKey'] = {'id': cursor}
        page = self.table.scan(**args)
        return page.get('Items', []), page.get('LastEvaluatedKey', {}).get('id')
    def update_task(self, key, status, updated_at):
        try:
            return self.table.update_item(Key={'id': key},
                UpdateExpression='SET #s = :s, updated_at = :u',
                ConditionExpression='attribute_exists(id) AND #k = :k',
                ExpressionAttributeNames={'#s': 'status', '#k': 'kind'},
                ExpressionAttributeValues={':s': status, ':u': updated_at, ':k': 'task'},
                ReturnValues='ALL_NEW')['Attributes']
        except Exception as exc:
            if getattr(exc, 'response', {}).get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                raise Missing() from exc
            raise

_store = None
_store_key = None

def get_store():
    global _store, _store_key
    key = ('local', os.environ.get('DB_PATH', 'data/cloudops.db')) if os.environ.get('LOCAL_MODE') == 'true' else ('aws', os.environ.get('TABLE_NAME'))
    if key != _store_key:
        _store = SQLiteStore(key[1]) if key[0] == 'local' else DynamoStore()
        _store_key = key
    return _store
