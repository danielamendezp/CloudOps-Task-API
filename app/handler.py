"""Asset inventory and maintenance tasks; API Gateway HTTP API v2 compatible."""
import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs
from app.storage import get_store, Missing

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def now():
    return datetime.now(timezone.utc).isoformat()

def response(status, body):
    return {'statusCode': status, 'headers': {'content-type': 'application/json'}, 'body': json.dumps(body)}

def text(data, key, maximum, required=True):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
        raise ValueError(f'{key} must contain {1 if required else 0}–{maximum} characters')
    return value.strip()

def valid_id(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('invalid UUID') from exc

def body(event):
    raw = event.get('body') or '{}'
    if event.get('isBase64Encoded'):
        raw = base64.b64decode(raw, validate=True).decode()
    if len(raw.encode()) > 16384:
        raise ValueError('body exceeds 16 KiB')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('JSON object required')
    return data

def handler(event, context):
    request_id = getattr(context, 'aws_request_id', 'local')
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('rawPath', '')
    logger.info(json.dumps({'request_id': request_id, 'method': method, 'path': path}))
    try:
        if method == 'GET' and path == '/health':
            return response(200, {'status': 'ok'})
        if path not in ('/assets', '/tasks') and not path.startswith(('/assets/', '/tasks/')):
            return response(404, {'error': 'route not found'})
        parts = path.strip('/').split('/')
        if len(parts) > 2:
            return response(404, {'error': 'route not found'})
        kind = {'assets': 'asset', 'tasks': 'task'}[parts[0]]
        store = get_store()
        if method == 'POST' and len(parts) == 1:
            data = body(event)
            item = {'id': str(uuid.uuid4()), 'kind': kind, 'created_at': now()}
            if kind == 'asset':
                item.update(name=text(data, 'name', 120), service=text(data, 'service', 60),
                            project=text(data, 'project', 80), reference=text(data, 'reference', 250, False),
                            environment=text(data, 'environment', 40, False) or 'personal')
            else:
                item.update(title=text(data, 'title', 120), status='open',
                            priority=data.get('priority', 'medium'))
                if item['priority'] not in ('low', 'medium', 'high'):
                    raise ValueError('priority must be low, medium or high')
                if data.get('asset_id'):
                    item['asset_id'] = valid_id(data['asset_id'])
                    if not store.get(item['asset_id'], 'asset'):
                        return response(404, {'error': 'asset not found'})
            store.put(item)
            return response(201, item)
        if method == 'GET' and len(parts) == 1:
            query = event.get('queryStringParameters') or {k: v[0] for k,v in parse_qs(event.get('rawQueryString', '')).items()}
            limit = int(query.get('limit', '25'))
            if not 1 <= limit <= 100:
                raise ValueError('limit must be between 1 and 100')
            cursor = valid_id(query['cursor']) if query.get('cursor') else None
            items, cursor = store.list(kind, limit, cursor)
            return response(200, {'items': items, 'next_cursor': cursor})
        if len(parts) == 2:
            key = valid_id(parts[1])
            if method == 'GET':
                item = store.get(key, kind)
                return response(200, item) if item else response(404, {'error': f'{kind} not found'})
            if method == 'PATCH' and kind == 'task':
                data = body(event)
                if set(data) != {'status'} or data['status'] not in ('open', 'in_progress', 'done'):
                    raise ValueError('provide only status: open, in_progress or done')
                return response(200, store.update_task(key, data['status'], now()))
        return response(405, {'error': 'method not allowed'})
    except Missing:
        return response(404, {'error': 'task not found'})
    except (ValueError, UnicodeError) as exc:
        return response(400, {'error': str(exc)})
    except Exception:
        logger.exception('request failed: %s', request_id)
        return response(500, {'error': 'internal error', 'request_id': request_id})
