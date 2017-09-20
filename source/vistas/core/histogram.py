import numpy


class Histogram:
    """ Internal representation of a histogram. Internally handles array masking and ranges. """

    def __init__(self, data=None, min_value=None, max_value=None, nodata_value=None):
        if data is None:
            data = numpy.zeros(1)
        self.data = data
        self.min_value = min_value
        self.max_value = max_value
        self.nodata_value = nodata_value

    def generate_histogram(self, bins):
        rng = None
        if all(x is not None for x in (self.min_value, self.max_value)):
            rng = (self.min_value, self.max_value)

        if self.nodata_value is None:
            return numpy.histogram(self.data, bins, range=rng)[0]
        else:
            return numpy.histogram(self.data[self.data != self.nodata_value], bins, range=rng)[0]
