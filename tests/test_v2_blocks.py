from copy import deepcopy
from types import SimpleNamespace

import pytest

from anytype import Block, Object, Space, Text, Heading1, Math, Code, Table, Type
from anytype import blocks
from anytype.api import ResponseHasError, apiEndpoints


KINDS = '''paragraph heading_1 heading_2 heading_3 heading_4 header_4 quote code title
 description checkbox bulleted_list_item numbered_list_item toggle callout toggle_heading_1
 toggle_heading_2 toggle_heading_3 file image video audio pdf bookmark link divider row column
 group table embed equation table_of_contents property dataview widget chat featured_properties icon'''.split()


@pytest.mark.parametrize('kind', KINDS)
def test_every_documented_kind_has_a_block_subclass(kind):
    data = {'type': kind, 'id': 'full-id', 'indent': 1}
    block = Block.from_dict(data)
    assert type(block) is not Block
    assert isinstance(block, Block)
    assert block.to_dict() == data
    assert block.to_dict(for_create=True) == {'type': kind, 'indent': 1}


def test_nested_table_and_unknown_blocks_roundtrip_without_aliasing():
    data = {'type': 'table', 'id': 'table', 'columns': [{'id': 'column'}],
            'rows': [{'id': 'row', 'cells': [[{'type': 'paragraph', 'text': 'cell'}]]}]}
    block = Block.from_dict(data)
    block.rows[0]['cells'][0][0]['text'] = 'changed'
    assert data['rows'][0]['cells'][0][0]['text'] == 'cell'
    inserted = block.to_dict(for_create=True)
    assert inserted['columns'] == [{}]
    assert 'id' not in inserted['rows'][0]
    future = {'type': 'future_kind', 'new_field': {'values': [1, 2]}}
    assert Block.from_dict(future).to_dict() == future
    assert Table(rows=[{'cells': [Text('nested')]}]).to_dict()['rows'][0]['cells'][0]['text'] == 'nested'


def test_content_helpers_build_typed_blocks():
    obj = Object('Example', 'page')
    obj.add_text('hello')
    obj.add_title1('Heading')
    obj.add_codeblock('print(1)', 'python')
    obj.add_math('x^2')
    assert [type(b) for b in obj.blocks] == [Text, Heading1, Code, Math]
    doc = obj.to_document()
    assert doc['formatVersion'] == '2.0'
    assert doc['properties']['name'] == 'Example'
    assert doc['blocks'][-1] == {'type': 'equation', 'text': 'x^2', 'processor': 'latex'}
    assert 'body' not in doc and 'type_key' not in doc


@pytest.mark.parametrize('indent', [-1, 33, True, 1.5])
def test_invalid_indent_rejected(indent):
    with pytest.raises(ValueError):
        Text('hello', indent=indent)


class MemoryAPI:
    def __init__(self):
        self.document = {'id': 'obj', 'type': 'page', 'formatVersion': '2.0', 'etag': 'etag-1',
                         'properties': {'name': 'Before', 'custom': False},
                         'blocks': [{'id': 'block-1', 'type': 'paragraph', 'text': 'Before'}]}
        self.calls = []

    def getObject(self, *args, **kwargs):
        return deepcopy(self.document)

    def updateObject(self, space, oid, data, **kwargs):
        self.calls.append((space, oid, data, kwargs))
        for op in data['ops']:
            if op['op'] == 'set_properties':
                self.document['properties'].update(op.get('set', {}))
                for key in op.get('unset', []):
                    del self.document['properties'][key]
            elif op['op'] == 'update_block':
                self.document['blocks'][0].update(op['set'])
            elif op['op'] == 'insert_blocks':
                self.document['blocks'].extend({'id': f'new-{i}', **b} for i, b in enumerate(op['blocks']))
        self.document['etag'] = 'etag-2'
        return {'etag': 'etag-2'}


def test_space_update_sends_minimal_atomic_patch_and_etag():
    backend = MemoryAPI()
    space = Space._from_api(backend, {'id': 'space'})
    obj = space.get_object('obj')
    obj.name = 'After'
    obj.blocks[0].text = 'After'
    obj.add_text('Appended')
    updated = space.update_object(obj)
    assert backend.calls == [('space', 'obj', {'ops': [
        {'op': 'set_properties', 'set': {'name': 'After'}},
        {'op': 'update_block', 'id': 'block-1', 'set': {'text': 'After'}},
        {'op': 'insert_blocks', 'blocks': [{'type': 'paragraph', 'text': 'Appended'}]},
    ]}, {'etag': 'etag-1'})]
    assert updated.etag == 'etag-2'
    assert isinstance(updated.blocks[-1], Text)
    space.update_object(updated)
    assert len(backend.calls) == 1


def test_dry_run_does_not_reload_or_mutate_object():
    backend = MemoryAPI()
    obj = Object._from_api(backend, backend.document | {'space_id': 'space'})
    original = deepcopy(obj._snapshot)
    obj.patch([{'op': 'set_properties', 'set': {'name': 'Changed'}}], dry_run=True)
    assert obj._snapshot == original
    assert obj.name == 'Before'
    assert backend.calls[-1][-1]['dry_run'] is True


def test_partial_rows_and_markdown_cannot_replace_existing_content():
    backend = MemoryAPI()
    space = Space._from_api(backend, {'id': 'space'})
    row = Object._from_api(backend, {'id': 'obj', 'type': 'page', 'name': 'row'})
    with pytest.raises(ValueError, match='Retrieve'):
        space.update_object(row)
    obj = space.get_object('obj')
    obj.markdown = 'replacement'
    with pytest.raises(ValueError, match='markdown'):
        space.update_object(obj)
    assert not backend.calls


def test_collection_and_query_use_v2_routes(monkeypatch):
    calls = []
    api = apiEndpoints()
    monkeypatch.setattr(api, '_request', lambda *a, **kw: calls.append((a, kw)))
    api.getObjectsInList('s', 'c', 'v', 5, 10)
    assert calls[-1] == (('GET', '/spaces/s/collections/c/objects'),
                         {'params': {'offset': 5, 'limit': 10, 'view': 'v'}})
    api.getListViews('s', 'q', kind='query')
    assert calls[-1][0] == ('GET', '/spaces/s/queries/q/views')
    api.deleteObjectsFromList('s', 'c', 'o')
    assert calls[-1][1]['json'] == {'ops': [{'op': 'remove_items', 'items': ['o']}]}


def test_etag_conflict_keeps_local_snapshot(monkeypatch):
    backend = MemoryAPI()
    obj = Object._from_api(backend, backend.document | {'space_id': 'space'})
    response = SimpleNamespace(status_code=409, json=lambda: {'code': 'etag_mismatch', 'message': 'changed'})
    def conflict(*args, **kwargs):
        raise ResponseHasError(response)
    monkeypatch.setattr(backend, 'updateObject', conflict)
    with pytest.raises(ResponseHasError) as error:
        obj.update_block(obj.blocks[0], text='new')
    assert error.value.status_code == 409
    assert obj.etag == 'etag-1'
    assert obj.blocks[0].text == 'Before'
