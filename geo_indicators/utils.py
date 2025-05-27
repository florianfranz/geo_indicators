import os
import rasterio
from rasterio.warp import reproject, calculate_default_transform, Resampling
from pyproj import CRS
import geopandas as gpd
import pandas as pd


def get_input_raster_path():
    """
    Get the absolute path of the input raster file (inside the data folder)
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # One level above current file
    data_dir = os.path.join(project_root, 'data')  # 'data' folder at the project root
    input_raster = os.path.join(data_dir, 'ETOPO_2022_global_ice_r0.1.tif')

    return input_raster

def get_reproj_latitudes_bounds_path():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # One level above current file
    data_dir = os.path.join(project_root, 'data')
    input_latitudes_path = os.path.join(data_dir, 'reproj_latitudes.geojson')

    return input_latitudes_path

def load_reproj_latitudes_bounds(file_path):
    gdf = gpd.read_file(file_path)

    return gdf


def get_reprojected_raster_path():
    """
    Get the absolute path to the reprojected raster (that will be saved inside the 'data' folder).
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    reprojected_raster = os.path.join(data_dir,
                                      'reprojected_ETOPO_2022_global_ice.tif')
    return reprojected_raster

def load_tiff(file_path):
    """
    load the .tif raster from the file_path, return the data and associated metadata
    """
    with rasterio.open(file_path) as src:
        data = src.read()
        metadata = src.meta
        src.close()
    return data, metadata


def reproject_raster(input_raster, output_raster, target_crs="ESRI:54034"):
    """
    Reproject the raster from its original CRS (EPSG:4326) to a target CRS with meters units (here ESRI:54034) using rasterio and pyproj.

    Parameters:
    - input_raster (str): Path to the input raster file.
    - output_raster (str): Path to save the reprojected raster.
    - target_crs (str): The target CRS to reproject to (default is EPSG:54034).
    """
    print(f"Opening input raster at: {input_raster}")  # Debug print

    with rasterio.open(input_raster) as src:
        src_crs = src.crs

        # Create the target CRS object using pyproj
        target_proj = CRS(target_crs)

        # Calculate the transform, width, and height for the new CRS
        transform, width, height = calculate_default_transform(
            src_crs, target_proj, src.width, src.height, *src.bounds
        )

        # Create the output raster with the new CRS and transform
        with rasterio.open(output_raster, 'w', driver='GTiff', height=height, width=width,
                           count=src.count, dtype=src.dtypes[0], crs=target_proj, transform=transform) as dst:
            for i in range(1, src.count + 1):  # Loop through each band in the raster
                # Reproject the data from the source CRS to the target CRS
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_crs=src_crs,
                    dst_crs=target_proj,
                    resampling=Resampling.nearest
                )


def get_panalesis_maps(version):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    version_dir = os.path.join(data_dir, f'pan_{version}')

    # List all files in the directory and filter for .tif files
    tif_files = [
        os.path.join(version_dir, f)
        for f in os.listdir(version_dir)
        if os.path.isfile(os.path.join(version_dir, f)) and f.lower().endswith('.tif')
    ]

    return tif_files


def get_panalesis_age(file_path):
    # Extract the filename from the path
    filename = os.path.basename(file_path)

    # Remove the extension
    name_without_ext = os.path.splitext(filename)[0]

    # Split by underscores and get the last part
    last_part = name_without_ext.split('_')[-1]

    try:
        age = int(last_part)
        return age
    except ValueError:
        raise ValueError(f"Filename does not end with a numeric age: {filename}")

def get_output_csv_path(source,version):
    """
    Get the absolute path to the reprojected raster (that will be saved inside the 'data' folder).
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    out_dir = os.path.join(data_dir, 'output')
    if source == "PANALESIS":
        out_csv = os.path.join(out_dir, f"stats_PANALESIS_{version}.csv")
    else:
        out_csv = os.path.join(out_dir, f'stats_{version}.csv')
    return out_csv

def stat_out(df, join_on,version,source):
    """
    Appends or creates a CSV file with new statistical data merged on a common key.

    Parameters:
    - df (pd.DataFrame): DataFrame containing the new data.
    - join_on (str): Column name to use as the join key (e.g., 'Age').
    """
    out_csv = get_output_csv_path(source,version)

    if os.path.exists(out_csv):
        existing_df = pd.read_csv(out_csv)
        updated_df = pd.merge(existing_df, df, on=join_on, how='left')
        updated_df.sort_values(by=join_on, inplace=True)
        updated_df.to_csv(out_csv, index=False)
    else:
        df.to_csv(out_csv, index=False)

