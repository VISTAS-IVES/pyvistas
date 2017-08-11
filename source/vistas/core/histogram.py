import numpy


class Histogram:
    """ Internal representation of a histogram. Internally handles array masking and ranges. """

    def __init__(self, data=None, nodata_value=None):
        if data is None:
            data = numpy.zeros(1)
        self.data = data
        self.nodata_value = nodata_value

    def generate_histogram(self, bins):
        data = self.data

        rng = None
        if isinstance(data, numpy.ma.MaskedArray):
            rng = (data.min(), data.max())

        if self.nodata_value is None:
            return numpy.histogram(self.data, bins, range=rng)[0]
        else:
            return numpy.histogram(self.data[self.data != self.nodata_value], bins, range=rng)[0]
