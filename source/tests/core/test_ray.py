import numpy
from pyrr import Vector3

from vistas.core.bounds import BoundingBox
from vistas.core.graphics.camera import Camera
from vistas.core.graphics.raycaster import Ray


def test_intersects_bbox():
    bbox = BoundingBox(0, 0, 0, 100, 100, 20)
    origin = Vector3(numpy.array([105, 105, 25], dtype=numpy.float32))
    world_origin = Vector3(numpy.array([0, 0, 0], dtype=numpy.float32))
    up = Vector3([0, 0, 1], numpy.float32)
    c = Camera()
    c.look_at(origin, world_origin, up)
    direction = c.get_direction()
    ray = Ray(origin, direction)
    assert ray.intersects_bbox(bbox)
    ray.origin = -origin                    # Move ray past bbox
    assert not ray.intersects_bbox(bbox)
    ray.direction = -direction              # Now look at it from opposite side
    assert ray.intersects_bbox(bbox)


def test_intersect_triangles():
    origin = Vector3(numpy.array([10, 10, 10], dtype=numpy.float32))
    world_origin = Vector3(numpy.array([0, 0, 0], dtype=numpy.float32))
    up = Vector3([0, 0, 1], numpy.float32)
    c = Camera()
    c.look_at(origin, world_origin, up)
    direction = c.get_direction()
    ray = Ray(origin, direction)

    vertices = numpy.array([
        [2, 0, 0],
        [0, 2, 0],
        [0, 0, 2],
        [2, 0, 0],
        [2, 2, 0],
        [2, 0, 0],
        [-2, 0, 0],
        [0, -2, 0],
        [0, 0, -2]],
        dtype=numpy.float32
    )

    faces = numpy.array([
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8]
    ], dtype=numpy.uint8)
    v1, v2, v3 = numpy.rollaxis(vertices[faces], axis=-2)

    distances, intersections = ray.intersect_triangles(v1, v2, v3)
    assert len(distances) == len(intersections) == 2
    assert 1 not in intersections
    assert {0, 2} == set(intersections)     # ensure the second triangle was not hit
