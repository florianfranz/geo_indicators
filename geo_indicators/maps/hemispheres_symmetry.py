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

def get_hemispheres_mask(raster_meta, raster_shape):
    """
    Generate a binary mask where True indicates pixels either north of Polar_N or south of Polar_S.
    """
    latitudes_path = get_reproj_latitudes_bounds_path()
    gdf = load_reproj_latitudes_bounds(latitudes_path)

    required_lines = ['Equator']
    if not all(name in gdf['name'].values for name in required_lines):
        raise ValueError("GeoJSON must contain both 'Polar_N' and 'Polar_S' lines.")

    northern_mask = np.zeros(raster_shape, dtype=bool)
    southern_mask = np.zeros(raster_shape, dtype=bool)

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

        if name == 'Equator':
            rows = np.where(rasterized == 1)[0]
            if rows.size > 0:
                northern_mask |= ys <= rows.min()
                southern_mask |= ys > rows.max()

    return northern_mask, southern_mask

def process_hemispheres_area():
    """
    Process the input raster to calculate both hemispheres land areas after reprojection.

    Returns:
    - tuple: (northern and southern hemispheres land area m²)
    """
    # Dynamically get the paths for input and reprojected raster
    input_raster = get_input_raster_path()
    reprojected_raster = get_reprojected_raster_path()

    # Reproject the raster before processing
    reproject_raster(input_raster, reprojected_raster)

    # Load the reprojected raster data
    data, metadata = load_tiff(reprojected_raster)
    transform = metadata['transform']


    pixel_area = abs(transform[0] * transform[4])  # pixel width × height in meters
    elevation = data[0]

    # Land mask: elevation >= 0
    land_mask = elevation >= 0

    # Get polar region mask
    northern_mask, southern_mask = get_hemispheres_mask(metadata, elevation.shape)

    # Combined mask: land AND within polar regions
    land_northern_mask = np.logical_and(land_mask, northern_mask)
    land_southern_mask = np.logical_and(land_mask, southern_mask)

    plt.figure(figsize=(10, 6))
    plt.imshow(land_northern_mask, cmap='Greys', interpolation='none')
    plt.title("Land Pixels in Northern hemisphere")
    plt.xlabel("X (pixel index)")
    plt.ylabel("Y (pixel index)")
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10, 6))
    plt.imshow(land_southern_mask, cmap='Greys', interpolation='none')
    plt.title("Land Pixels in Southern hemisphere")
    plt.xlabel("X (pixel index)")
    plt.ylabel("Y (pixel index)")
    plt.tight_layout()
    plt.show()

    # Area calculations
    total_area = elevation.size * pixel_area
    northern_land_area = np.sum(land_northern_mask) * pixel_area
    southern_land_area = np.sum(land_southern_mask) * pixel_area

    return total_area, northern_land_area,southern_land_area

if __name__ == "__main__":
    total_area, northern_land_area,southern_land_area = process_hemispheres_area()
    northern_percentage = northern_land_area / total_area * 100
    southern_percentage = southern_land_area / total_area * 100
    land_area_ratio = northern_land_area / southern_land_area


    print(f"Total raster area: {total_area:.2e} m²")
    print(f"Northern land area: {northern_land_area:.2e} m²")
    print(f"Percentage of northern land: {northern_percentage:.2f}%")
    print(f"Southern land area: {southern_land_area:.2e} m²")
    print(f"Percentage of southern land: {southern_percentage:.2f}%")
    print(f"Land area ratio (Northern/Southern): {land_area_ratio:.2f}")









