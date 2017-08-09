from pyrr import Vector3


def cubic_interpolation(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t) -> Vector3:
    """ Obtain the cubic interpolation between 3 vectors as a vector along the parametric parameter t. """
    t2 = t * t
    a = p3 - p2 - p0 + p1
    return a * t * t2 + (p0 - p1 - a) * t2 + (p2 - p0) * t + p1


def catmull_rom_splines(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t) -> Vector3:
    """ Obtain the catmull rom spline between 3 vectors as a vector along the parametric parameter t. """
    t2 = t * t
    a0 = p0 * -0.5 + p1 * 1.5 + p2 * -1.5 + p3 * 0.5
    a1 = p0 - p1 * 2.5 + p2 * 2.0 - p3 * 0.5
    a2 = p0 * -0.5 + p2 * 0.5
    a3 = p1
    return a0 * t * t2 + a1 * t2 + a2 * t + a3
