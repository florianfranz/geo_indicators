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

def get_polar_mask(raster_meta, raster_shape):
    """
    Generate a binary mask where True indicates pixels either north of Polar_N or south of Polar_S.
    """
    latitudes_path = get_reproj_latitudes_bounds_path()
    gdf = load_reproj_latitudes_bounds(latitudes_path)

    required_lines = ['Polar_N', 'Polar_S']
    if not all(name in gdf['name'].values for name in required_lines):
        raise ValueError("GeoJSON must contain both 'Polar_N' and 'Polar_S' lines.")

    polar_mask = np.zeros(raster_shape, dtype=bool)

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

        coords = np.indices(raster_shape)
        ys = coords[0]

        if name == 'Polar_N':
            rows = np.where(rasterized == 1)[0]
            if rows.size > 0:
                polar_mask |= ys < rows.min()
        elif name == 'Polar_S':
            rows = np.where(rasterized == 1)[0]
            if rows.size > 0:
                polar_mask |= ys > rows.max()

    return polar_mask

def process_polar_area():
    """
    Process the input raster to calculate total and polar land areas after reprojection.

    Returns:
    - tuple: (land area m², total area m², polar land area m²)
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

    # Get polar region mask
    polar_mask = get_polar_mask(metadata, elevation.shape)

    # Combined mask: land AND within polar regions
    combined_mask = np.logical_and(land_mask, polar_mask)
    plt.figure(figsize=(10, 6))
    plt.imshow(combined_mask, cmap='Greys', interpolation='none')
    plt.title("Land Pixels in Polar Regions")
    plt.xlabel("X (pixel index)")
    plt.ylabel("Y (pixel index)")
    plt.tight_layout()
    plt.show()

    # Area calculations
    total_area = elevation.size * pixel_area
    polar_land_area = np.sum(combined_mask) * pixel_area

    return total_area, polar_land_area

if __name__ == "__main__":
    total_area, polar_land_area = process_polar_area()
    polar_percentage = polar_land_area / total_area * 100

    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Polar land area: {polar_land_area:.2e} m²")
    print(f"Percentage of polar land: {polar_percentage:.2f}%")





