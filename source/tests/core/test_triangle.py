from pyrr import Vector3

from vistas.core.math import Triangle


def test_barycoord_from_pos():
    a = Vector3([10, 10, 0])
    b = Vector3([10, 0, 0])
    c = Vector3([0, 10, 0])
    tri = Triangle(a, b, c)

    p1 = Vector3([7.5, 7.5, 0])
    result = tri.barycoord_from_pos(p1)
    assert result == Vector3([0.5, 0.25, 0.25])
    assert sum(result) == 1

    p2 = Vector3()
    result = tri.barycoord_from_pos(p2)
    assert tri.barycoord_from_pos(p2) == Vector3([-1, 1, 1])
    assert sum(result) == 1


def test_contains_point():
    a = Vector3([10, 10, 0])
    b = Vector3([10, 0, 0])
    c = Vector3([0, 10, 0])
    tri = Triangle(a, b, c)

    p1 = Vector3([7.5, 7.5, 0])
    assert tri.contains_point(p1)

    p2 = Vector3()
    assert not tri.contains_point(p2)

    p3 = Vector3([0, 0, 10])
    assert not tri.contains_point(p3)
