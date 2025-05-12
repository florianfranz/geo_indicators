import numpy as np
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path
from geo_indicators.visualization import plot_mask


def process_shelves_area():
    """
    Process the input raster to calculate continental shelves area after reprojection.

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
    transform = metadata['transform']

    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    shelves_mask = (data[0] >= -300) & (data[0] < 0)  # Mask the pixels where the elevation is between -300 and 0m
    plot_mask(shelves_mask, "Continental Shelves (-300m >= z > 0m)")

    # Calculate area (count of pixels * pixel area)
    shelves_area = np.sum(shelves_mask) * pixel_area
    total_area = data[0].size * pixel_area

    return shelves_area, total_area


if __name__ == "__main__":

    shelves_area, total_area = process_shelves_area()
    shelves_percentage = shelves_area/total_area*100
    print(f"Total shelves area: {shelves_area:.2e} m²")
    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Percentage of shelves is {shelves_percentage}")
