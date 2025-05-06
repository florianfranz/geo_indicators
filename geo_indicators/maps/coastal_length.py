from skimage import measure
from shapely.geometry import Polygon, Point
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt

from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path


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

def create_contours():
    """
        Process the input raster to create coastline contours.

        Returns:
        -a geodataframe (gdf) with all contour features
        """
    # Dynamically get the paths for input and reprojected raster
    input_raster = get_input_raster_path()
    reprojected_raster = get_reprojected_raster_path()

    # Reproject the raster before processing
    reproject_raster(input_raster, reprojected_raster)

    # Load the reprojected raster data
    data, metadata = load_tiff(reprojected_raster)

    with rasterio.open(reprojected_raster) as src:
        transform = src.transform
    polygons = []
    contours = measure.find_contours(data[0], 0)
    for contour in contours:
        transformed_contour = []
        for point in contour:
            x, y = transform * (point[1], point[0])  # Transform to geographic coordinates
            transformed_contour.append((x, y))

        # Close the contour if needed
        closed_contour = close_contour(transformed_contour)
        if closed_contour:
            polygon = Polygon(closed_contour)
            if polygon.is_valid:
                polygons.append({'geometry': polygon, 'level': 0})
    gdf = gpd.GeoDataFrame(polygons)
    gdf.set_crs('ESRI:54034', allow_override=True)

    return gdf


def calculate_total_length(gdf):
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


if __name__ == "__main__":
    coastlines = create_contours()
    coastlines.plot(edgecolor='black', facecolor='none', linewidth=0.5)
    plt.title("Detected Coastlines")
    plt.xlabel("Longitude (in meters)")
    plt.ylabel("Latitude (in meters)")

    plt.show()
    total_coastline_length = calculate_total_length(coastlines)
    print(f"Total coastline length is {total_coastline_length} m")