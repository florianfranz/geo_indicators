import numpy as np
from geo_indicators.visualization import plot_passage
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
    return np.flipud(mask[0])  # First band and flip vertically

def horizontal_sections(transect):
    """
    Identify horizontal sea passages (start and end) in a longitudinal transect.
    """
    west_edges = []
    east_edges = []

    for lon in range(len(transect)):
        if transect[lon] == 0:  # Sea
            if lon == 0 or transect[lon - 1] == 1:
                west_edges.append(lon)
            if lon == len(transect) - 1 or transect[lon + 1] == 1:
                east_edges.append(lon)

    steps = []
    for i in range(len(west_edges)):
        center = int((west_edges[i] + east_edges[i]) / 2)
        width = east_edges[i] - west_edges[i]
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
    Build the best north-south sea routes across the map.
    """
    steps = horizontal_sections(sea_mask[0, :])
    if not steps:
        return []

    routes = [[step] for step in steps]

    for lat in range(1, sea_mask.shape[0]):
        steps = horizontal_sections(sea_mask[lat, :])
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


if __name__ == '__main__':
    raster_path = get_input_raster_path()
    elevation_data, metadata = load_tiff(raster_path)
    nodata_value = metadata.get('nodata', None)
    sea_mask = build_sea_mask(elevation_data, nodata_value=nodata_value)
    routes = find_routes(sea_mask)
    plot_passage(sea_mask,routes)
