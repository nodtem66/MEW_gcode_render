import argparse
import csv
import math
import os
from pathlib import Path

from mew_gcode_render.gcode_reader import parse_gcode
from mew_gcode_render.geometry_parser import GeometryParser


def mapCoordinates(p: list[float], cylindrical_long_axis: str, xy_scale: float) -> dict[str, float]:
    x = xy_scale * p[0]
    y = xy_scale * p[1]
    z = xy_scale * p[2] if len(p) > 2 else 0

    if cylindrical_long_axis == "x":
        return {"mapX": x, "mapY": y, "mapZ": z}
    elif cylindrical_long_axis == "y":
        return {"mapX": y, "mapY": x, "mapZ": z}
    elif cylindrical_long_axis == "z":
        return {"mapX": z, "mapY": y, "mapZ": x}
    raise ValueError(f"Invalid cylindrical_long_axis: {cylindrical_long_axis}")


def transformToCylindrical(p: list[float], diameter: float, cylindrical_long_axis: str, xy_scale: float):
    mapped_coords = mapCoordinates(p, cylindrical_long_axis, xy_scale)

    radius = diameter / 2.0
    height = radius + mapped_coords["mapZ"]
    theta = mapped_coords["mapY"] / radius if radius > 0 else mapped_coords["mapY"] / 0.001
    longitudinalAxis = mapped_coords["mapX"]
    # Convert cylindrical to Cartesian coordinates
    x = longitudinalAxis
    y = xy_scale * height * math.cos(theta)
    z = xy_scale * height * math.sin(theta)
    return [x, y, z]


def read_gcode_file(filename: str) -> list:
    """
    Parameter:
        filename: The path to the gcode file to read.
    Return:
        a list of gcode commands parsed from the given file.
    throws:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is empty or contains no valid gcode commands.
    """
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        raise FileNotFoundError(f"File {filename} does not exist.")

    with open(filename, "r") as f:
        gcodes = [parse_gcode(line) for line in f]

    if len(gcodes) == 0:
        print("No gcode commands found in the file.")
        raise ValueError("No gcode commands found in the file.")

    return gcodes


def gcode_to_points(
    gcodes: list,
    csv_filename: str,
    diameter: float,
    thickness: float,
    cylindrical_long_axis: str,
    curve_resolution: int,
    x_axis: str,
    y_axis: str,
    z_axis: str,
):

    xy_scale = 1.0 if thickness == 0 else (diameter + thickness) / diameter

    geometry_parser = GeometryParser()
    geometry_parser.x_axis = x_axis
    geometry_parser.y_axis = y_axis
    geometry_parser.z_axis = z_axis
    geometry_parser.process(gcodes)

    print(len(geometry_parser.geometry), "curves parsed from gcode")

    geometry_points = []
    for curve in geometry_parser.geometry:
        points = curve.compute_points(curve_resolution)
        if diameter > 0:
            transformed_points = [transformToCylindrical(p, diameter, cylindrical_long_axis, xy_scale) for p in points]
            geometry_points.extend(transformed_points)
        else:
            geometry_points.extend(points)

    return geometry_points


def write_points_to_csv(points: list[list[float]], csv_filename: str):
    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["x", "y", "z"])
        writer.writerows(points)

    print("Exported to", csv_filename)


def main():
    parser = argparse.ArgumentParser(description="Export gcode to csv")
    parser.add_argument("filename", help="Gcode file to export to csv")
    parser.add_argument("-d", "--diameter", type=float, help="Diameter of the tube in mm", default=0)
    parser.add_argument("-t", "--thickness", type=float, help="Thickness of the tube in mm", default=0)
    parser.add_argument("-x", "--x_axis", type=str, help="Axis to use for x coordinate (default: x)", default="x")
    parser.add_argument("-y", "--y_axis", type=str, help="Axis to use for y coordinate (default: y)", default="y")
    parser.add_argument("-z", "--z_axis", type=str, help="Axis to use for z coordinate (default: z)", default="z")
    parser.add_argument(
        "-c",
        "--cylindrical_long_axis",
        type=str,
        help="Axis to use as the long axis for cylindrical transformation (default: none)",
        default="x",
        choices=["x", "y", "z"],
    )
    parser.add_argument(
        "-r",
        "--curve_resolution",
        type=int,
        help="Number of points to sample per curve segment (default: 20)",
        default=20,
    )
    args = parser.parse_args()

    gcodes = read_gcode_file(args.filename)
    csv_filename = Path(args.filename).with_suffix(".csv")
    geometry_points = gcode_to_points(
        gcodes,
        csv_filename,
        args.diameter,
        args.thickness,
        cylindrical_long_axis=args.cylindrical_long_axis,
        curve_resolution=args.curve_resolution,
        x_axis=args.x_axis,
        y_axis=args.y_axis,
        z_axis=args.z_axis,
    )

    write_points_to_csv(geometry_points, csv_filename)
    print("Done!")
