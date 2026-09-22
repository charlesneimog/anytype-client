"""Opt in with ANYTYPE_V2_LIVE=1 and ANYTYPE_API_KEY; uses the space named API."""
import os
import uuid

import pytest

from anytype import Anytype, Object, Type, Text, Heading1, Heading2, Code, Math, Checkbox, Callout, Table, Toggle, apiEndpoints
from anytype.api import ResponseHasError
from anytype.property import Date, Select

pytestmark = pytest.mark.skipif(os.environ.get('ANYTYPE_V2_LIVE') != '1', reason='live API opt-in')


def test_api_space_v2_lifecycle():
    token = os.environ['ANYTYPE_API_KEY']
    client = Anytype()
    client._apiEndpoints = apiEndpoints({'Authorization': f'Bearer {token}'})
    spaces = client.get_spaces()
    space = client.get_space(next(s for s in spaces if s.name == os.getenv('ANYTYPE_SPACE_NAME', 'API')))
    suffix = uuid.uuid4().hex[:10]
    objects, types, properties = [], [], []
    try:
        prop = Date('v2 date ' + suffix)
        prop.key = 'v2_date_' + suffix
        prop = space.create_property(prop)
        properties.append(prop.key)
        assert prop.format == 'date'
        select = Select('v2 status ' + suffix)
        select.key = 'v2_status_' + suffix
        select.options = [{'name': 'Draft', 'color': 'blue'}]
        select = space.create_property(select)
        properties.append(select.key)
        assert select.get_tags()[0].name == 'Draft'
        custom = Type('v2 test ' + suffix)
        custom.plural_name = 'v2 tests'
        custom.add_property(prop)
        custom.add_property(select)
        custom = space.create_type(custom)
        types.append(custom.key)
        custom.plural_name = 'Updated tests'
        custom = space.update_type(custom)
        assert custom.plural_name == 'Updated tests'
        obj = Object('v2 test ' + suffix, custom, blocks=[
            Text('Hello **v2**'), Heading1('First'), Heading2('Second'),
            Code('print(1)', language='python'), Math('x^2'), Checkbox('done', checked=False),
            Callout('Notice', icon={'format': 'emoji', 'emoji': '💡'}),
            Toggle('Parent'), Text('Child', indent=1),
            Table(columns=[{}, {}], rows=[{'cells': ['A', 'B']}]),
        ])
        obj.properties[prop.name].value = '2026-09-21'
        obj.properties[select.name].value = 'Draft'
        dry = space.create_object(obj, dry_run=True)
        assert dry['dry_run']
        obj = space.create_object(obj)
        objects.append(obj.id)
        assert len(obj.blocks) == 10
        assert obj.properties[prop.key].startswith('2026-09-21')
        assert obj.properties[select.key] == ['Draft']
        stale = space.get_object(obj.id)
        obj.name += ' updated'
        obj.blocks[0].text = 'Updated v2'
        obj.add_text('Appended')
        space.update_object(obj)
        assert obj.blocks[0].text == 'Updated v2'
        assert obj.blocks[-1].text == 'Appended'
        with pytest.raises(ResponseHasError) as error:
            stale.update_block(stale.blocks[0], text='stale')
        assert error.value.status_code == 409
        obj.update_block(obj.blocks[-1], text='Patched')
        assert obj.blocks[-1].text == 'Patched'
        obj.delete_block(obj.blocks[-1])
        assert len(obj.blocks) == 10
        collection = space.create_collection('v2 collection ' + suffix, [obj])
        objects.append(collection.id)
        view = space.get_listviews(collection)[0]
        assert view.get_objectsinlistview()[0].id == obj.id
        view.delete_objectinlistview(obj)
        assert not space.get_list_objects(collection)
        view.add_objectinlistview(obj)
        assert space.get_list_objects(collection)[0].id == obj.id
        query = space.create_query('v2 query ' + suffix, custom)
        objects.append(query.id)
        assert space.get_listviews(query, kind='query')
        assert any(row.id == obj.id for row in space.get_list_objects(query, kind='query'))
        assert space.search(obj.name, type=custom)
        assert 'Updated v2' in obj.markdown
        assert client.global_search(obj.name, type=custom.key)
    finally:
        # Only resources created during this test are eligible for cleanup.
        for oid in reversed(objects):
            space.delete_object(oid)
        for key in reversed(types):
            space.delete_type(key)
        for key in reversed(properties):
            space._apiEndpoints.deleteProperty(space.id, key)
