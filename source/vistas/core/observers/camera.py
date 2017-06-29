from vistas.core.observers.interface import Observable
from vistas.ui.utils import post_redisplay


class CameraObservable(Observable):

    _camera_observable = None

    @classmethod
    def get(cls):
        if cls._camera_observable is None:
            cls._camera_observable = CameraObservable()
        return cls._camera_observable

    is_sync = False
    need_state_saved = False
    global_interactor = None

    def sync_camera(self, interactor, save_state):
        self.is_sync = True
        self.need_state_saved = save_state
        self.global_interactor = interactor
        self.notify_observers()
        post_redisplay()

    def unsync_camera(self):
        self.is_sync = False
        self.need_state_saved = False
        self.global_interactor = None
        self.notify_observers()
        post_redisplay()
