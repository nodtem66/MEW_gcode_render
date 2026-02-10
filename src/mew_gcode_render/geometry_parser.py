import math

from mew_gcode_render.gcode_reader import GcodeCommand

RELATIVE_POSITION = 0
ABSOLUTE_POSITION = 1


def linspace(start: float, stop: float, num: int = 10) -> list[float]:
    """
    linspace(start, stop, num) returns num evenly spaced samples, calculated over the interval [start, stop].
    If num is 1, the function returns an array containing only the start value. If num is 0, the function returns an empty array.
    Args:
        - start: The starting value of the sequence.
        - stop: The end value of the sequence.
        - num: The number of samples to generate. Must be a non-negative integer. Default is 10.
    Return:
        An array of num evenly spaced samples, calculated over the interval [start, stop].
    Example:
    >>> linspace(0, 10, 5)
    array([ 0.,  2.5,  5.,  7.5, 10.])
    """
    match num:
        case _ if num < 0:
            raise ValueError("num must be a non-negative integer")
        case 0:
            return []
        case 1:
            return [start]
        case _:
            step = (stop - start) / (num - 1)
            return [start + i * step for i in range(num)]


class Curve:
    """Class representing a curve segment."""

    def __init__(self, type: str, start: list[float], end: list[float], feedrate: float, **kwargs):
        self.type = type
        self.start = start
        self.end = end
        self.feedrate = feedrate
        for key, value in kwargs.items():
            setattr(self, key, value)

    def compute_points(self, num_points=20):
        """
        Get a list of points along the curve.
        Parameters:
            num_points: number of points to generate along the curve (default: 20)
        Returns:
            list of points along the curve
        """
        if self.type == "line":
            x_points = linspace(self.start[0], self.end[0], num_points)
            y_points = linspace(self.start[1], self.end[1], num_points)
            if len(self.start) > 2 and len(self.end) > 2:
                z_points = linspace(self.start[2], self.end[2], num_points)
                return [[x, y, z] for x, y, z in zip(x_points, y_points, z_points)]
            else:
                return [[x, y, 0] for x, y in zip(x_points, y_points)]
        elif self.type == "arc":
            center_x, center_y = self.center
            radius = math.sqrt((self.start[0] - center_x) ** 2 + (self.start[1] - center_y) ** 2)
            start_angle = math.atan2(self.start[1] - center_y, self.start[0] - center_x)
            end_angle = math.atan2(self.end[1] - center_y, self.end[0] - center_x)

            angleCalc = end_angle - start_angle
            isCw = self.dir == "cw"
            if isCw and angleCalc > 0:
                angleCalc -= 2 * math.pi
            elif not isCw and angleCalc < 0:
                angleCalc += 2 * math.pi

            if abs(angleCalc) < 1e-3:
                angleCalc = 2 * math.pi if not isCw else -2 * math.pi

            points = []
            for i in range(num_points + 1):
                t = i / num_points
                angle = start_angle + t * angleCalc
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                if len(self.start) > 2 and len(self.end) > 2:
                    z = self.start[2] + t * (self.end[2] - self.start[2])
                else:
                    z = 0
                points.append([x, y, z])
            return points
        else:
            raise ValueError(f"Unsupported curve type: {self.type}")


class GeometryParser:
    """Class to parse GCode commands into geometry."""

    position: dict[str, float]
    positionSystem: int
    feedrate: float
    geometry: list[Curve]
    x_axis: str
    y_axis: str
    z_axis: str
    lineCount: int

    def __init__(self):
        self.position = {"x": 0, "y": 0, "z": 0}
        self.positionSystem = ABSOLUTE_POSITION
        self.feedrate = 100
        self.geometry = []
        self.cursorPosition = []
        self.x_axis = "x"
        self.y_axis = "y"
        self.z_axis = "z"
        self.lineCount = 0

    def reset(self):
        self.position = {"x": 0, "y": 0, "z": 0}
        self.geometry = []
        self.positionSystem = ABSOLUTE_POSITION
        self.feedrate = 100

    def process(self, gcode_array: list[GcodeCommand]):
        """Process an array of gcode commands."""
        for x in gcode_array:
            self.lineCount += 1
            if x.cmd and hasattr(self, x.cmd):
                method = getattr(self, x.cmd)
                method(x.args)
            if x.tag:
                self.processComment(x.tag)

    def isRelativePosition(self):
        return self.positionSystem == RELATIVE_POSITION

    def isAbsolutePosition(self):
        return self.positionSystem == ABSOLUTE_POSITION

    def processComment(self, tag):
        for key, val in tag.items():
            if key == "CTS":
                self.feedrate = val

    def getAxisValue(self, args, axis):
        axis_attr = axis + "_axis"
        if hasattr(self, axis_attr):
            axis_key = getattr(self, axis_attr)
            if axis_key in args:
                return args[axis_key]
        if axis in args:
            return args[axis]
        return None

    def getAllAxesValues(self, args):
        vals = {"x": 0, "y": 0, "z": 0}
        if self.isAbsolutePosition():
            val_x = self.getAxisValue(args, "x")
            val_y = self.getAxisValue(args, "y")
            val_z = self.getAxisValue(args, "z")
            vals["x"] = val_x if val_x is not None else self.position["x"]
            vals["y"] = val_y if val_y is not None else self.position["y"]
            vals["z"] = val_z if val_z is not None else self.position["z"]
        elif self.isRelativePosition():
            vals["x"] = self.position["x"] + (self.getAxisValue(args, "x") or 0)
            vals["y"] = self.position["y"] + (self.getAxisValue(args, "y") or 0)
            vals["z"] = self.position["z"] + (self.getAxisValue(args, "z") or 0)
        return vals

    def G0(self, args):
        prev_position = self.position.copy()
        vals = self.getAllAxesValues(args)
        self.position["x"] = vals["x"]
        self.position["y"] = vals["y"]
        self.position["z"] = vals["z"]

        self.geometry.append(
            Curve(
                type="line",
                start=[prev_position["x"], prev_position["y"], prev_position["z"]],
                end=[self.position["x"], self.position["y"], self.position["z"]],
                feedrate=args.get("f", self.feedrate),
            )
        )

    def G1(self, args):
        self.G0(args)

    def G2(self, args, dir="cw"):
        prev_position = self.position.copy()
        vals = self.getAllAxesValues(args)
        self.position["x"] = vals["x"]
        self.position["y"] = vals["y"]
        self.position["z"] = vals["z"]

        center_x = args.get("i", 0)
        center_y = args.get("j", 0)
        if self.isRelativePosition():
            center_x += prev_position["x"]
            center_y += prev_position["y"]

        self.geometry.append(
            Curve(
                type="arc",
                dir=dir,
                start=[prev_position["x"], prev_position["y"], prev_position["z"]],
                end=[self.position["x"], self.position["y"], self.position["z"]],
                center=[center_x, center_y],
                feedrate=args.get("f", self.feedrate),
            )
        )

    def G3(self, args):
        self.G2(args, "ccw")

    def G90(self, _):
        self.positionSystem = ABSOLUTE_POSITION

    def G91(self, _):
        self.positionSystem = RELATIVE_POSITION
