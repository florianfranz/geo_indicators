import numpy as np
import rasterio
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path


def process_area():
    """
    Process the input raster to calculate an area after reprojection.

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

    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    land_mask = data[0] >= 0  # Mask the pixels where the elevation is above or equal to sea level

    # Calculate area (count of pixels * pixel area)
    land_area = np.sum(land_mask) * pixel_area
    total_area = data[0].size * pixel_area


    return land_area, total_area


if __name__ == "__main__":

    land_area, total_area = process_area()
    land_percentage = land_area/total_area*100
    print(f"Total land area: {land_area:.2e} m²")
    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Percentage of land is {land_percentage}")
