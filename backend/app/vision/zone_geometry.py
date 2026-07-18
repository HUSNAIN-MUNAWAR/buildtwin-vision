from shapely.geometry import Point, Polygon


def validate_polygon(points: list[list[float]]) -> None:
    if len(points) < 3:
        raise ValueError("A zone polygon requires at least three points")
    polygon = Polygon(points)
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError("Zone polygon is invalid or has zero area")


def point_inside(points: list[list[float]], x: float, y: float) -> bool:
    validate_polygon(points)
    return Polygon(points).contains(Point(x, y))


def box_centroid_inside(points: list[list[float]], box: dict) -> bool:
    return point_inside(points, (box["x1"] + box["x2"])/2, (box["y1"] + box["y2"])/2)
