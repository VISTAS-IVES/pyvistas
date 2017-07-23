from shapely.ops import triangulate, transform
import shapely.geometry as geometry
from functools import partial

def test():
    import fiona
    import time
    p = r'C:\Users\taylor\Documents\pyvistas_testdata\graysharbor_dem\IDU.shp'
    start = time.time()
    with fiona.open(p, 'r') as shp:
        shapes = [s for s in shp]
        meta = shp.meta

    geometries = []
    for s in shapes:
        coords = s['geometry']['coordinates']
        geo = geometry.shape(s['geometry'])
        geometries.append(geo)
    end = time.time() - start
    print("Num geometries: {}".format(len(geometries)))
    print("Elapsed: {}".format(end))
    tris = [triangulate(t) for t in geometries]
    end = time.time() - start
    print("Elapsed: {}".format(end))
    return tris



