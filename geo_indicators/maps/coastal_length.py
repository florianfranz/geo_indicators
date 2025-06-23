import os
from skimage import measure
from shapely.geometry import Polygon
import pandas as pd
import geopandas as gpd
from geo_indicators.visualization import plot_gdf_simple, plot_timeseries_simple
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out
)



def close_contour(contour):
    """
    Ensures that a contour line is closed to form a valid polygon.
    For contours spanning near the antimeridian, close them by adding intermediate points
    at the antimeridian (-180 or 180) to form a properly closed polygon.
    """
    if len(contour) < 3:
        return None  # Not enough points to form a polygon

    # Get first and last points
    first_lon, first_lat = contour[0]
    last_lon, last_lat = contour[-1]

    # Determine the pole latitude based on the hemisphere of the contour
    pole_lat = -6360338.2938046408817172 if last_lat < 0 else 6360338.2938046408817172

    # Define longitude threshold for detecting near-antimeridian points
    lon_threshold = 19982002.33 #based on a 179.5 threshold for a 180 longitude value, rescaled to WCEA (World Cylindrical Equal Area) projection values

    # Check if the contour spans the antimeridian
    if first_lon <= -lon_threshold and last_lon >= lon_threshold:
        # First point near -180 and last point near 180
        contour.append((20037508.3427892439067364, last_lat))  # Add point at the WCEA projection east border with last latitude
        contour.append((20037508.3427892439067364, pole_lat))  # Add point at the WCEA projection east border and the pole
        contour.append((-20037508.3427892439067364, pole_lat))  # Add point at the WCEA projection west border and the pole
        contour.append((-20037508.3427892439067364, first_lat))  # Add point at the WCEA projection wast border with first latitude

    elif first_lon >= lon_threshold and last_lon <= -lon_threshold:
        # First point near 180 and last point near -180
        contour.append((-20037508.3427892439067364, last_lat))  # Add point at WCEA projection wast border with last latitude
        contour.append((-20037508.3427892439067364, pole_lat))  # Add point at WCEA projection wast border and the pole
        contour.append((20037508.3427892439067364, pole_lat))  # Add point at WCEA projection east border and the pole
        contour.append((20037508.3427892439067364, first_lat))  # Add point at WCEA projection east border with first latitude

    # Ensure the contour is a closed loop
    if contour[0] != contour[-1]:
        contour.append(contour[0])

    return contour

def create_contours(data, transform, level):
    """
    Process the input raster to create coastline contours.

    Returns:
    - a GeoDataFrame (gdf) with all contour features, or an empty GeoDataFrame if no contours are found.
    """
    polygons = []
    contours = measure.find_contours(data[0], level)

    if not contours:
        return gpd.GeoDataFrame(geometry=[], crs='ESRI:54034')

    for contour in contours:
        transformed_contour = []
        for point in contour:
            x, y = transform * (point[1], point[0])  # Transform to geographic coordinates
            transformed_contour.append((x, y))

        closed_contour = close_contour(transformed_contour)
        if closed_contour:
            polygon = Polygon(closed_contour)
            if polygon.is_valid:
                polygons.append({'geometry': polygon, 'level': level})

    if not polygons:
        return gpd.GeoDataFrame(geometry=[], crs='ESRI:54034')

    gdf = gpd.GeoDataFrame(polygons)
    gdf = gdf.set_geometry('geometry')
    gdf.set_crs('ESRI:54034', allow_override=True)

    return gdf



def get_total_length(gdf):
    """
    Calculates the total length of all features in the GeoDataFrame.

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame with polygon geometries.

    Returns:
        float: Total perimeter length in meters.
    """
    # Ensure geometry is valid and in a projected CRS
    if gdf.crs is None:
        gdf.set_crs('ESRI:54034', allow_override=True)

    # Convert polygons to boundaries and calculate lengths
    total_length = gdf.geometry.boundary.length.sum()

    return total_length

def process_coastal_length(source,version,verbose=False):
    ages = []
    total_coastline_lengths = []
    if source == "ETOPO":
        if version != "ETOPO_2022":
            version = "ETOPO_2022"
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        age = 0
        ages.append(age)
        coastlines = create_contours(data,transform,0)
        if verbose:
            plot_gdf_simple(coastlines, "Coastlines")
        total_coastline_length = get_total_length(coastlines)
        total_coastline_lengths.append(total_coastline_length)
        if verbose:
            print(f"Total coastline length is {total_coastline_length} m")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            coastlines = create_contours(data, transform,0)
            total_coastline_length = get_total_length(coastlines)
            total_coastline_lengths.append(total_coastline_length)
        combined = list(zip(ages, total_coastline_lengths))
        combined.sort(key=lambda x: x[0])
        ages, total_coastline_lengths = zip(*combined)
        if verbose:
            plot_timeseries_simple(ages, total_coastline_lengths, "Total Coastal Length (m)", "Coastal Length vs Age")
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")
    df = pd.DataFrame({
        'Age': ages,
        'Coastline_length': total_coastline_lengths
    })
    stat_out(df, join_on='Age', version=version, source=source)
if __name__ == "__main__":
    source = "ETOPO"
    version = "v1"
    process_coastal_length(source,version)