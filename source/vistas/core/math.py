from vistas.core.graphics.vector import Vector


def cubic_interpolation(p0: Vector, p1: Vector, p2: Vector, p3: Vector, t) -> Vector:
    t2 = t * t
    a = p3 - p2 - p0 + p1
    return a*t*t2 + (p0 - p1 - a)*t2 + (p2 - p0)*t + p1


def catmull_rom_splines(p0: Vector, p1: Vector, p2: Vector, p3: Vector, t) -> Vector:
    t2 = t*t
    a0 = p0 * -0.5 + p1 * 1.5 + p2 * -1.5 + p3 * 0.5
    a1 = p0 - p1 * 2.5 + p2 * 2.0 - p3 * 0.5
    a2 = p0 * -0.5 + p2 * 0.5
    a3 = p1
    return a0*t*t2+a1*t2+a2*t+a3
