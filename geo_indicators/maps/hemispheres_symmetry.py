import os
import numpy as np
import pandas as pd
from rasterio.features import rasterize
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_reproj_latitudes_bounds_path,
    load_reproj_latitudes_bounds,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out
)
from geo_indicators.visualization import plot_mask, plot_timeseries_double

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

def get_hemispheres_area(data,metadata,transform,plot=False):
    """
    Process the input raster to calculate both hemispheres land areas after reprojection.

    Returns:
    - tuple: (northern and southern hemispheres land area m²)
    """
    pixel_area = abs(transform[0] * transform[4])  # pixel width × height in meters
    elevation = data[0]

    # Land mask: elevation >= 0
    land_mask = elevation >= 0

    # Get polar region mask
    northern_mask, southern_mask = get_hemispheres_mask(metadata, elevation.shape)

    # Combined mask: land AND within polar regions
    land_northern_mask = np.logical_and(land_mask, northern_mask)
    land_southern_mask = np.logical_and(land_mask, southern_mask)
    if plot == True:
        plot_mask(land_northern_mask, "Land Pixels in Northern Hemisphere")
        plot_mask(land_southern_mask, "Land Pixels in Southern Hemisphere")

    # Area calculations
    total_area = elevation.size * pixel_area
    northern_land_area = np.sum(land_northern_mask) * pixel_area
    southern_land_area = np.sum(land_southern_mask) * pixel_area

    return total_area, northern_land_area,southern_land_area

def process_hemispheres_area(source,version,verbose=False):
    ages = []
    southern_land_areas = []
    northern_land_areas = []
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
        if verbose:
            total_area, northern_land_area, southern_land_area = get_hemispheres_area(data,metadata,transform, plot=True)
        else:
            total_area, northern_land_area, southern_land_area = get_hemispheres_area(data, metadata, transform,
                                                                                      plot=False)
        northern_land_areas.append(northern_land_area)
        southern_land_areas.append(southern_land_area)
        northern_percentage = northern_land_area / total_area * 100
        southern_percentage = southern_land_area / total_area * 100
        land_area_ratio = northern_land_area / southern_land_area
        if verbose:
            print(f"Total raster area: {total_area:.2e} m²")
            print(f"Northern land area: {northern_land_area:.2e} m²")
            print(f"Percentage of northern land: {northern_percentage:.2f}%")
            print(f"Southern land area: {southern_land_area:.2e} m²")
            print(f"Percentage of southern land: {southern_percentage:.2f}%")
            print(f"Land area ratio (Northern/Southern): {land_area_ratio:.2f}")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            total_area, northern_land_area, southern_land_area = get_hemispheres_area(data, metadata, transform, plot=False)
            northern_land_areas.append(northern_land_area)
            southern_land_areas.append(southern_land_area)
            northern_percentage = northern_land_area / total_area * 100
            southern_percentage = southern_land_area / total_area * 100
            land_area_ratio = northern_land_area / southern_land_area
            if verbose:
                print(map)
                print(f"Total raster area: {total_area:.2e} m²")
                print(f"Northern land area: {northern_land_area:.2e} m²")
                print(f"Percentage of northern land: {northern_percentage:.2f}%")
                print(f"Southern land area: {southern_land_area:.2e} m²")
                print(f"Percentage of southern land: {southern_percentage:.2f}%")
                print(f"Land area ratio (Northern/Southern): {land_area_ratio:.2f}")
        combined = list(zip(ages, northern_land_areas, southern_land_areas))
        combined.sort(key=lambda x: x[0])
        ages, northern_land_areas, southern_land_areas = zip(*combined)
        if verbose:
            plot_timeseries_double(
                ages,
                northern_land_areas, 'Northern Land Area (m²)',
                southern_land_areas, 'Southern Land Area (m²)',
                'Northern and Southern Land Area vs Age'
            )
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")
    df = pd.DataFrame({
        'Age': ages,
        'Northern_Land_Area': northern_land_areas,
        'Southern_Land_Area': southern_land_areas
    })
    stat_out(df, join_on='Age', version=version, source=source)

if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    process_hemispheres_area(source, version)









