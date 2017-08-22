import json
from io import StringIO
from unittest.mock import patch, mock_open, MagicMock

from vistas.core import stats

var_data = {
    'min_value': 1.3362300395965576,
    'max_value': 30.22311019897461,
    'nodata_value': -9999.0,
    'shape': [67, 86]
}

cache_data = {
    'stats': {'test_data': var_data},
    'last_modified': 10.0,
    'checksum': '123'
}


def test_to_dict():
    vs = stats.VariableStats(123, 321, None, {'custom': 'data'})
    assert vs.to_dict == {'min_value': 123, 'max_value': 321, 'nodata_value': None, 'custom': 'data'}


def test_from_dict():
    vs = stats.VariableStats.from_dict(var_data)
    assert vs.min_value == var_data.get('min_value')
    assert vs.max_value == var_data.get('max_value')
    assert vs.nodata_value == var_data.get('nodata_value')
    assert vs.misc == {'shape': [67, 86]}


@patch('vistas.core.stats.compute_file_checksum', MagicMock(return_value='123'))
@patch('time.time', MagicMock(return_value=10.0))
def test_save():
    with patch('{}.open'.format(stats.__name__), mock_open(read_data='{}')) as open_mock:
        open_mock.return_value = StringIO()
        open_mock().close = MagicMock()
        ps = stats.PluginStats({'test_data': stats.VariableStats.from_dict(var_data)})
        ps.save('cache.json', 'data.asc')
        assert json.loads(open_mock().getvalue()) == cache_data
        assert ps.is_stale is False


def test_load():
    with patch('{}.open'.format(stats.__name__), mock_open(read_data=json.dumps(cache_data))):

        # Assume checksums are same
        with patch('vistas.core.stats.compute_file_checksum', MagicMock(return_value='123')):

            # Test that data is at least as old as the cache
            with patch('os.path.getmtime', MagicMock(return_value=10.0)):
                ps = stats.PluginStats.load('cache.json', 'data.asc', ['test_data'])
                assert ps.is_stale is False

            # Test that the data is younger than the cache, but checksum is same
            with patch('os.path.getmtime', MagicMock(return_value=11.0)):
                ps = stats.PluginStats.load('cache.json', 'data.asc', ['test_data'])
                assert ps.is_stale is False

        # Assume checksums are different (i.e. the file was modified)
        with patch('vistas.core.stats.compute_file_checksum', MagicMock(return_value='321')):

            # Test that data is younger than the cache
            with patch('os.path.getmtime', MagicMock(return_value=100.0)):
                ps = stats.PluginStats.load('cache.json', 'data.asc', ['test_data'])
                assert ps.is_stale
