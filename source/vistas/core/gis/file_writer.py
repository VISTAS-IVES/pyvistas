from collections import OrderedDict
from osgeo.osr import SpatialReference

import numpy


class RasterWriter:
    """ An interface for writing various raster data formats. """

    @staticmethod
    def write_esri_grid_ascii_file(path, data, extent, cellsize, nodata_value=-9999.0):
        xllcorner, yllcorner, *_ = extent.as_list()
        nrows, ncols = data.shape

        header_dict = OrderedDict()
        header_dict['nrows'] = nrows
        header_dict['ncols'] = ncols
        header_dict['xllcorner'] = xllcorner
        header_dict['yllcorner'] = yllcorner
        header_dict['cellsize'] = cellsize
        header_dict['nodata_value'] = nodata_value
        header = '\n'.join(['{} {}'.format(key, val) for key, val in header_dict.items()])

        numpy.savetxt(path, data, header=header, comments='')

        # save projection info to adjacent file
        ref = SpatialReference()
        ref.ImportFromProj4(extent.projection.srs)
        with open(path.replace('asc', 'prj'), 'w') as f:
            f.write(ref.ExportToWkt())
