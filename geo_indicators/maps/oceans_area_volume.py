import numpy as np
import rasterio
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path


def oceans_area_volume(data, transform):
    """
    Calculate the area and volume of pixels below sea level (elevation < 0).

    Parameters:
    - data (numpy.ndarray): The raster data array.
    - transform (Affine): The affine transformation of the raster (from rasterio).

    Returns:
    - tuple: (area in square meters, volume in cubic meters).
    """
    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    mask = data < 0  # Mask the pixels where the elevation is below sea level

    # Calculate area (count of pixels * pixel area)
    area = np.sum(mask) * pixel_area

    # Calculate volume (sum of absolute elevation values * pixel area)
    volume = np.sum(np.abs(data[mask])) * pixel_area

    return area, volume


def process_area_volume():
    """
    Process the input raster to calculate area and volume below sea level after reprojection.

    Returns:
    - tuple: (area in square meters, volume in cubic meters).
    """
    # Dynamically get the paths for input and reprojected raster
    input_raster = get_input_raster_path()
    reprojected_raster = get_reprojected_raster_path()

    # Reproject the raster before processing
    reproject_raster(input_raster, reprojected_raster)

    # Load the reprojected raster data
    data, metadata = load_tiff(reprojected_raster)

    # Assuming 'transform' is in metadata, otherwise, fetch it from the rasterio object
    with rasterio.open(reprojected_raster) as src:
        transform = src.transform

    area, volume = oceans_area_volume(data[0], transform)  # data[0] is the first band

    return area, volume


# Example usage
if __name__ == "__main__":
    area, volume = process_area_volume()
    print(f"Area below sea level: {area:.2e} m²")
    print(f"Volume below sea level: {volume:.2e} m³")
