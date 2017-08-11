import threading
from time import sleep

import wx.lib.newevent

ThreadSyncEvent, EVT_THREAD_SYNC = wx.lib.newevent.NewEvent()


class Thread(threading.Thread, wx.EvtHandler):
    """ Base threading class. Enables event-based synchronization of the worker thread with the main thread. """

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        wx.EvtHandler.__init__(self)

        self.Bind(EVT_THREAD_SYNC, self.on_sync)

    def sync_with_main(self, func, args=(), kwargs={}, block=False, delay=0):
        thread_event = threading.Event()
        event = ThreadSyncEvent(func=func, args=args, kwargs=kwargs, event=thread_event)

        wx.PostEvent(self, event)

        if block:
            thread_event.wait()
            if delay:
                sleep(delay)

    def on_sync(self, event):
        event.func(*event.args, **event.kwargs)

        event.event.set()
