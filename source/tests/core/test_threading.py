from unittest.mock import MagicMock, patch

from tests.fixtures import generic_app
from vistas.core import threading
from vistas.core.threading import ThreadSyncEvent

generic_app  # Make the fixture import look used to IDEs


def test_sync_with_main(generic_app):
    def run_test():
        thread = threading.Thread()
        sync_fn = MagicMock()

        with patch('{}.wx.PostEvent'.format(threading.__name__)) as post_mock:
            thread.sync_with_main(sync_fn)
            assert post_mock.called
            assert isinstance(post_mock.call_args[0][1], ThreadSyncEvent)
            assert post_mock.call_args[0][1].func is sync_fn

    generic_app(run_test)
