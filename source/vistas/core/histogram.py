import numpy


class Histogram:

    def __init__(self, data):
        if data is None:
            data = numpy.zeros(1)
        self.data = data

    def generate_histogram(self, bins):
        return numpy.histogram(self.data, bins)[0]
