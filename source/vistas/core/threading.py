import threading

import wx.lib.newevent

ThreadSyncEvent, EVT_THREAD_SYNC = wx.lib.newevent.NewEvent()


class Thread(threading.Thread, wx.PyEvtHandler):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        wx.PyEvtHandler.__init__(self)

        self.Bind(EVT_THREAD_SYNC, self.on_sync)

    def sync_with_main(self, func, args=(), kwargs={}, block=False):
        thread_event = threading.Event()
        event = ThreadSyncEvent(func=func, args=args, kwargs=kwargs, event=thread_event)

        wx.PostEvent(self, event)

        if block:
            thread_event.wait()

    def on_sync(self, event):
        event.func(*event.args, **event.kwargs)

        event.event.set()
