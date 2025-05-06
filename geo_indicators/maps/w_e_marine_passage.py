import numpy as np
import matplotlib.pyplot as plt
from geo_indicators.utils import load_tiff, get_input_raster_path


SEA_LEVEL = 0
class Step:
    def __init__(self, center, width):
        self.center = center
        self.width = width

def build_sea_mask(elevation, nodata_value=None):
    """
    Convert elevation data to a binary land/sea mask.
    Land = 1, Sea = 0
    """
    if nodata_value is not None:
        elevation = np.where(elevation == nodata_value, np.nan, elevation)
    mask = np.where(np.isnan(elevation), 1, (elevation >= SEA_LEVEL).astype(int))
    return np.flipud(mask[0])  # Take first band and flip vertically

def vertical_sections(transect):
    """
    Identify vertical sea passages (start and end) in a latitudinal transect.
    """
    north_edges = []
    south_edges = []

    for lat in range(len(transect)):
        if transect[lat] == 0:  # Sea
            if lat == 0 or transect[lat - 1] == 1:
                north_edges.append(lat)
            if lat == len(transect) - 1 or transect[lat + 1] == 1:
                south_edges.append(lat)

    steps = []
    for i in range(len(north_edges)):
        center = int((north_edges[i] + south_edges[i]) / 2)
        width = south_edges[i] - north_edges[i]
        steps.append(Step(center, width))
    return steps

def free_passage(previous_route, new_step):
    """
    Compute the overlap between the last step in the current route and a new step.
    """
    return (previous_route[-1].width + new_step.width) / 2 - abs(previous_route[-1].center - new_step.center)

def minimum_width(route):
    """
    Find the minimum width in the route.
    """
    return min(step.width for step in route)

def find_routes(sea_mask):
    """
    Build the best east-west sea routes across the map.
    """
    steps = vertical_sections(sea_mask[:, 0])
    if not steps:
        return []

    routes = [[step] for step in steps]

    for lon in range(1, sea_mask.shape[1]):
        steps = vertical_sections(sea_mask[:, lon])
        if not steps:
            return []

        new_routes = []
        for step in steps:
            best_route = []
            best_width = 0
            for route in routes:
                passage = free_passage(route, step)
                route_min_width = minimum_width(route)
                if passage > 0 and route_min_width > best_width:
                    best_width = route_min_width
                    best_route = route
            if best_route:
                updated_route = best_route.copy()
                updated_route.append(step)
                new_routes.append(updated_route)

        if not new_routes:
            return []
        routes = new_routes
    return routes

def plot_best_passage(sea_mask):
    """
    Plot the sea mask and overlay the best passage in red.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(sea_mask, cmap='Blues', origin='lower')  # Sea=0, Land=1

    routes = find_routes(sea_mask)

    for route in routes:
        x_coords = range(len(route))
        y_coords = [step.center for step in route]
        ax.plot(x_coords, y_coords, color='red', linewidth=2)

    plt.xlabel('Longitude Index')
    plt.ylabel('Latitude Index')
    plt.title('Best Ocean Passage (Red)')
    plt.grid(True)
    plt.show()


if __name__ == '__main__':
    raster_path = get_input_raster_path()
    elevation_data, metadata = load_tiff(raster_path)
    nodata_value = metadata.get('nodata', None)
    sea_mask = build_sea_mask(elevation_data, nodata_value=nodata_value)
    plot_best_passage(sea_mask)
