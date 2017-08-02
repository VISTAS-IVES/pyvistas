import json
from unittest.mock import patch, mock_open, MagicMock

from io import StringIO
from pytest import fixture

from tests.fixtures import generic_app
from vistas.core import preferences

generic_app  # Make the fixture import look used to IDEs

@fixture(scope='function')
def preferences_cls():
    yield preferences.Preferences
    preferences.Preferences._app_preferences = None


@patch('os.path.exists')
def test_singleton_makedirs(mock_exists, preferences_cls, generic_app):
    with patch('{}.open'.format(preferences.__name__), mock_open(read_data='{}')):
        with patch('os.makedirs') as mock_makedirs:
            mock_exists.return_value = True
            preferences_cls.app()
            assert mock_makedirs.called is False
            preferences.Preferences._app_preferences = None

        with patch('os.makedirs') as mock_makedirs:
            mock_exists.return_value = False
            preferences_cls.app()
            assert mock_makedirs.called
            preferences.Preferences._app_preferences = None


@patch('os.path.exists', MagicMock(return_value=True))
def test_singleton_cache(preferences_cls, generic_app):
    with patch('{}.open'.format(preferences.__name__), mock_open(read_data='{}')):
        prefs = preferences_cls.app()
        assert preferences_cls.app() == prefs


@patch('os.path.exists', MagicMock(return_value=False))
def test_save():
    with patch('{}.open'.format(preferences.__name__), mock_open(read_data='{}')) as open_mock:
        open_mock.return_value = StringIO()
        open_mock().close = MagicMock()

        prefs = preferences.Preferences('prefs.json')
        prefs['key'] = 'value'

        assert open_mock().getvalue() == json.dumps({'key': 'value'})


@patch('os.path.exists', MagicMock(return_value=True))
def test_load():
    with patch('{}.open'.format(preferences.__name__), mock_open(read_data=json.dumps({'key': 'value'}))):
        prefs = preferences.Preferences('prefs.json')
        assert prefs['key'] == 'value'
