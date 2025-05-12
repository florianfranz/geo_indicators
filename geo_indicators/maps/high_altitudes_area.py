import numpy as np
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path
from geo_indicators.visualization import plot_mask


def process_high_altitudes_area():
    """
    Process the input raster to calculate high altitudes (>3000m) area after reprojection.

    Returns:
    - tuple: (area in square meters).
    """
    # Dynamically get the paths for input and reprojected raster
    input_raster = get_input_raster_path()
    reprojected_raster = get_reprojected_raster_path()

    # Reproject the raster before processing
    reproject_raster(input_raster, reprojected_raster)

    # Load the reprojected raster data
    data, metadata = load_tiff(reprojected_raster)
    transform = metadata['transform']


    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    high_altitude_mask = data[0] >= 3000  # Mask the pixels where the elevation is above 3000m
    plot_mask(high_altitude_mask, "High Altitude Regions (z >=3000m)")

    # Calculate area (count of pixels * pixel area)
    high_altitude_area = np.sum(high_altitude_mask) * pixel_area
    total_area = data[0].size * pixel_area


    return high_altitude_area, total_area


if __name__ == "__main__":

    high_altitude_area, total_area = process_high_altitudes_area()
    high_altitude_percentage = high_altitude_area/total_area*100
    print(f"Total high altitude area: {high_altitude_area:.2e} m²")
    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Percentage of high altitude regions is {high_altitude_percentage}")
