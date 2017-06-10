from PIL.Image import Image


class VideoEncoder:
    """ Video encoder interface. Implemented to provide a means of encoding frames to a video file. """

    def get_options(self):
        return None

    def open(self, path, width, height):
        """ Opens a stream to a file"""

        raise NotImplemented

    def write_frame(self, bitmap: Image, duration):
        """ Writes a frame to the stream for the duration, in seconds """

        raise NotImplemented

    def finalize(self):
        """ Finalize/close the stream """

        raise NotImplemented

    def set_framerate(self, fps):
        raise NotImplemented

    def is_ok(self):
        """ Returns True if this stream is open and is not in an error state """

        raise NotImplemented
