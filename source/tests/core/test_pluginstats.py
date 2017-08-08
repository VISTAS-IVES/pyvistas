from pytest import fixture

from vistas.core.plugins.stats import PluginStats, VariableStats

data = {
    'min_value': 1.3362300395965576,
    'max_value': 30.22311019897461,
    'nodata_value': -9999.0,
    'shape': [67, 86]
}


@fixture(scope='session')
def stats_file(tmpdir_factory):
    path = str(tmpdir_factory.mktemp('data').join('stats.json'))
    PluginStats({'test_data': VariableStats.from_dict(data)}).save(path)
    return path


def test_to_dict():
    vs = VariableStats(123, 321, None, {'custom': 'data'})
    assert vs.to_dict == {'min_value': 123, 'max_value': 321, 'nodata_value': None, 'custom': 'data'}


def test_from_dict():
    vs = VariableStats.from_dict(data)
    assert vs.min_value == data.get('min_value')
    assert vs.max_value == data.get('max_value')
    assert vs.nodata_value == data.get('nodata_value')
    assert vs.misc == {'shape': [67, 86]}


def test_save(tmpdir):
    path = tmpdir.mkdir('test').join('stats.json')
    vs = VariableStats.from_dict(data)
    ps = PluginStats({'test_data': vs})
    ps.save(str(path))
    assert len(tmpdir.listdir()) == 1


def test_load(stats_file):
    ps = PluginStats.load(stats_file, ['test_data'])
    assert len(ps) == 1
    assert ps['test_data'].to_dict == data
    assert ps['nonexistent_data'] is None


def test_is_stale(stats_file):
    ps = PluginStats()
    assert ps.is_stale

    vs = VariableStats.from_dict(data)
    ps = PluginStats({'test_data': vs})
    assert not ps.is_stale

    # Simulate data that has an unaccounted variable
    ps = PluginStats.load(stats_file, ['test_data', 'new_data'])
    assert ps.is_stale

    # Simulate an expired cache
    ps = PluginStats.load(stats_file, ['test_data'], expiration=0)
    assert ps.is_stale
