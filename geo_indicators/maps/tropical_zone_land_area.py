import numpy as np
import rasterio
from rasterio.features import rasterize
import matplotlib.pyplot as plt


from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_reproj_latitudes_bounds_path,
    load_reproj_latitudes_bounds
)

def get_tropical_mask(raster_meta, raster_shape):
    """
    Generate a binary mask where True indicates pixels between:
    - Subtropical_S and Subtropical_N
    """
    latitudes_path = get_reproj_latitudes_bounds_path()
    gdf = load_reproj_latitudes_bounds(latitudes_path)

    required_lines = ['Subtropical_N', 'Subtropical_S']
    if not all(name in gdf['name'].values for name in required_lines):
        raise ValueError("GeoJSON must contain all required latitude boundary lines.")

    line_rows = {}

    # Rasterize each line to find its row position
    for name in required_lines:
        geom = gdf[gdf['name'] == name].geometry
        if geom.empty:
            continue

        rasterized = rasterize(
            [(g, 1) for g in geom],
            out_shape=raster_shape,
            transform=raster_meta['transform'],
            fill=0,
            all_touched=True,
            dtype='uint8'
        )

        rows = np.where(rasterized == 1)[0]
        if rows.size > 0:
            line_rows[name] = rows.mean()  # average row if line spans multiple rows

    if len(line_rows) != 2:
        raise ValueError("Could not locate all required latitude boundaries in raster.")

    ys = np.indices(raster_shape)[0]
    tropical_mask = (ys >= line_rows['Subtropical_N']) & (ys <= line_rows['Subtropical_S'])

    return tropical_mask


def process_tropical_area():
    """
    Process the input raster to calculate total and tropical land areas after reprojection.

    Returns:
    - tuple: (land area m², total area m², tropical land area m²)
    """
    # Dynamically get the paths for input and reprojected raster
    input_raster = get_input_raster_path()
    reprojected_raster = get_reprojected_raster_path()

    # Reproject the raster before processing
    reproject_raster(input_raster, reprojected_raster)

    # Load the reprojected raster data
    data, metadata = load_tiff(reprojected_raster)

    # Fetch transform for pixel area
    with rasterio.open(reprojected_raster) as src:
        transform = src.transform

    pixel_area = abs(transform[0] * transform[4])  # pixel width × height in meters
    elevation = data[0]

    # Land mask: elevation >= 0
    land_mask = elevation >= 0

    # Get tropical region mask
    tropical_mask = get_tropical_mask(metadata, elevation.shape)

    # Combined mask: land AND within tropical region
    combined_mask = np.logical_and(land_mask, tropical_mask)
    plt.figure(figsize=(10, 6))
    plt.imshow(combined_mask, cmap='Greys', interpolation='none')
    plt.title("Land Pixels in Tropical Regions")
    plt.xlabel("X (pixel index)")
    plt.ylabel("Y (pixel index)")
    plt.tight_layout()
    plt.show()

    # Area calculations
    total_area = elevation.size * pixel_area
    tropical_land_area = np.sum(combined_mask) * pixel_area

    return total_area, tropical_land_area

if __name__ == "__main__":
    total_area, tropical_land_area = process_tropical_area()
    tropical_percentage = tropical_land_area / total_area * 100
    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Tropical land area: {tropical_land_area:.2e} m²")
    print(f"Percentage of tropical land: {tropical_percentage:.2f}%")
