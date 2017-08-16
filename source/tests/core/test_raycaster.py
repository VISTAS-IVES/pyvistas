from pyrr import Vector3
import numpy
from vistas.core.graphics.raycaster import Ray  #, Raycaster
from vistas.core.graphics.bounds import BoundingBox


def test_intersects_bbox():
    origin = Vector3(numpy.array([100, 100, 100], dtype=numpy.float32))
    direction = Vector3(numpy.array([-1, -1, -1], dtype=numpy.float32))
    direction.normalize()
    ray = Ray(origin, direction)
    bbox = BoundingBox(0, 0, 0, 10, 10, 10)
    assert ray.intersects_bbox(bbox)
    ray.origin.y += 100.0
    assert not ray.intersects_bbox(bbox)


def test_intersects_bbox2():
    origin = Vector3(numpy.array([430, 1340, 15], dtype=numpy.float32))
    direction = Vector3(numpy.array([0, 0, -1], dtype=numpy.float32))
    print(direction)
    ray = Ray(origin, direction)
    bbox = BoundingBox(0, 0, 0, 830, 670, 30)
    assert ray.intersects_bbox(bbox)
    ray.origin.y += 10.0
    assert ray.intersects_bbox(bbox)
    ray.origin.y += 100.0
    assert not ray.intersects_bbox(bbox)
