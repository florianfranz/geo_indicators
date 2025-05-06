import numpy as np
import rasterio
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path
import matplotlib.pyplot as plt


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

    # Assuming 'transform' is in metadata, otherwise, fetch it from the rasterio object
    with rasterio.open(reprojected_raster) as src:
        transform = src.transform

    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    shelves_mask = (data[0] >= -300) & (data[0] < 0)  # Mask the pixels where the elevation is between -300 and 0m

    # Calculate area (count of pixels * pixel area)
    shelves_area = np.sum(shelves_mask) * pixel_area
    total_area = data[0].size * pixel_area
    plt.figure(figsize=(10, 6))
    plt.imshow(shelves_mask, cmap='Greys', interpolation='none')
    plt.title("Continental Shelves")
    plt.xlabel("X (pixel index)")
    plt.ylabel("Y (pixel index)")
    plt.tight_layout()
    plt.show()


    return shelves_area, total_area


if __name__ == "__main__":

    shelves_area, total_area = process_shelves_area()
    shelves_percentage = shelves_area/total_area*100
    print(f"Total shelves area: {shelves_area:.2e} m²")
    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Percentage of shelves is {shelves_percentage}")
