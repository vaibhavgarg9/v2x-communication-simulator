"""
V2V Communication Utilities for SUMO Simulation
Handles vehicle-to-vehicle communication geometry calculations
"""

from shapely.geometry import Polygon
from shapely.affinity import rotate, translate

def create_vehicle_polygon(x_position, y_position, heading, length, width):
    """
    Create a polygon representing a vehicle's position and orientation
    Args:
        x_position (float): X coordinate of vehicle center
        y_position (float): Y coordinate of vehicle center
        heading (float): Vehicle heading in degrees
        length (float): Vehicle length in meters
        width (float): Vehicle width in meters
    Returns:
        Shapely Polygon object representing the vehicle
    """
    half_length = length / 2.0
    half_width = width / 2.0
    
    # Create rectangle at (0,0) then rotate about its center
    rect = Polygon([
        (-half_length, -half_width),
        (half_length, -half_width),
        (half_length, half_width),
        (-half_length, half_width)
    ])
    
    # Rotate first, then translate to correct position
    rotated = rotate(rect, heading, origin=(0, 0), use_radians=False)
    return translate(rotated, xoff=x_position, yoff=y_position)

def find_distance(vehicle_a, vehicle_b):
    """
    Calculate edge-to-edge distance between two vehicles
    Args:
        vehicle_a, vehicle_b (dict): Vehicle data dictionaries
    Returns:
        float: Minimum distance between vehicles in meters
    """
    poly_a = create_vehicle_polygon(
        vehicle_a['x_position'], vehicle_a['y_position'],
        vehicle_a['heading'], vehicle_a['length'], vehicle_a['width']
    )
    poly_b = create_vehicle_polygon(
        vehicle_b['x_position'], vehicle_b['y_position'],
        vehicle_b['heading'], vehicle_b['length'], vehicle_b['width']
    )
    return poly_a.distance(poly_b)