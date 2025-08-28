"""
V2P Communication Utilities for SUMO Simulation
Handles vehicle-to-pedestrian communication geometry calculations
"""

from shapely.geometry import Point
from . import v2v_functions

def create_pedestrian_circle(center, radius):
    """
    Create a circular polygon representing a pedestrian
    Args:
        center (tuple): (x, y) coordinates of pedestrian position
        radius (float): Radius of pedestrian representation
    Returns:
        Shapely Polygon object representing the pedestrian
    """
    return Point(center).buffer(radius)

def find_v2p_distance(vehicle, pedestrian):
    """
    Calculate distance between vehicle and pedestrian
    Args:
        vehicle (dict): Vehicle data dictionary
        pedestrian (dict): Pedestrian data dictionary
    Returns:
        float: Minimum distance between vehicle and pedestrian
    """
    ped_radius = pedestrian["width"]/2
    veh_poly = v2v_functions.create_vehicle_polygon(
        vehicle["x_position"], vehicle["y_position"],
        vehicle["heading"], vehicle["length"], vehicle["width"]
    )
    ped_poly = create_pedestrian_circle(
        (pedestrian["x_position"], pedestrian["y_position"]), ped_radius
    )
    return veh_poly.distance(ped_poly)