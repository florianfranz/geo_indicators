import os
import pandas as pd
import numpy as np
from pysheds.grid import Grid
import gc
import json
import psutil
import subprocess
import traceback
import sys
import rasterio
from skimage.transform import rescale
from scipy.stats import skew, kurtosis
from geo_indicators.maps.coastal_length import create_contours
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out

)
from geo_indicators.maps.continents_number import filter_large_polygons
from geo_indicators.visualization import plot_histogram


def check_memory():
    """Monitor memory usage and warn if getting high"""
    memory = psutil.virtual_memory()
    if memory.percent > 85:
        gc.collect()
    return memory.percent


def get_flow_direction(grid, dem, dirmap):
    """Calculate flow direction with memory management"""
    check_memory()
    pit_filled_dem = grid.fill_pits(dem, epsilon=1e-3)
    check_memory()
    flooded_dem = grid.fill_depressions(pit_filled_dem, epsilon=1e-3)
    del pit_filled_dem
    gc.collect()
    inflated_dem = grid.resolve_flats(flooded_dem)
    del flooded_dem
    gc.collect()
    check_memory()
    flow_direction = grid.flowdir(inflated_dem, dirmap=dirmap, nodata_out=np.int64(0))
    del inflated_dem
    gc.collect()
    check_memory()

    return flow_direction


def get_catchment_areas_by_geometry(grid, gdf, acc, fdir, dirmap):
    """Process catchment areas for all geometries with memory management"""
    all_areas = []
    total_vertices = 0
    processed_vertices = 0

    for geom_idx, geom in enumerate(gdf.geometry):
        vertices = []

        if geom.geom_type == 'Polygon':
            vertices.extend(list(geom.exterior.coords))
            for interior in geom.interiors:
                vertices.extend(list(interior.coords))
        elif geom.geom_type == 'MultiPolygon':
            for part in geom.geoms:
                vertices.extend(list(part.exterior.coords))
                for interior in part.interiors:
                    vertices.extend(list(interior.coords))

        if not vertices:
            continue
        total_vertices += len(vertices)
        areas = get_catchment_areas_from_vertices(grid, vertices, acc, fdir, dirmap,
                                                  geom_idx, processed_vertices)
        all_areas.extend(areas)
        processed_vertices += len(vertices)
        check_memory()

    return all_areas


def get_catchment_areas_from_vertices(grid, vertices_list, acc, fdir, dirmap, geom_id=0, vertex_offset=0):
    """Process vertices in batches to manage memory with robust error handling"""
    catchment_areas = []
    batch_size = 20

    cell_width = abs(grid.affine.a)
    cell_height = abs(grid.affine.e)
    cell_area = cell_width * cell_height
    processed_count = 0
    error_count = 0

    for batch_num, batch_start in enumerate(range(0, len(vertices_list), batch_size)):
        batch_end = min(batch_start + batch_size, len(vertices_list))
        batch_vertices = vertices_list[batch_start:batch_end]
        for i, vertex in enumerate(batch_vertices):
            try:
                if isinstance(vertex, (tuple, list)) and len(vertex) >= 2:
                    x, y = float(vertex[0]), float(vertex[1])
                    x_snap, y_snap = grid.snap_to_mask(acc > 1000, (x, y))
                    catch = grid.catchment(
                        x=x_snap,
                        y=y_snap,
                        fdir=fdir,
                        dirmap=dirmap,
                        xytype='coordinate'
                    )
                    catch_array = catch.view()
                    num_cells = np.count_nonzero(catch_array)
                    if num_cells > 0:
                        catchment_area = num_cells * cell_area
                        catchment_areas.append(catchment_area)
                        processed_count += 1
                    del catch, catch_array

            except Exception as e:
                print(f"      Unexpected error: {e}", file=sys.stderr)
                print(f"      Error type: {type(e).__name__}", file=sys.stderr)
                error_count += 1
                continue
        gc.collect()

        if batch_num % 3 == 0:
            memory_percent = check_memory()
            if memory_percent > 90:
                print("Critical memory usage - stopping processing", file=sys.stderr)
                break
        if batch_num > 10 and error_count > processed_count * 2:
            print(f"Too many errors ({error_count} errors vs {processed_count} successful). Stopping.", file=sys.stderr)
            break

    return catchment_areas


def compute_catchment_statistics(areas):
    if not areas:
        raise ValueError("No areas provided for statistics computation")

    areas_array = np.array(areas)
    if len(areas_array) == 0:
        raise ValueError("Empty areas array")

    stats = {
        'count': len(areas_array),
        'mean': float(np.mean(areas_array)),
        'median': float(np.median(areas_array)),
        'min': float(np.min(areas_array)),
        'max': float(np.max(areas_array)),
        'std_dev': float(np.std(areas_array)),
        'variance': float(np.var(areas_array)),
        'skewness': float(skew(areas_array)),
        'kurtosis': float(kurtosis(areas_array)),
        'percentiles': {
            '10th': float(np.percentile(areas_array, 10)),
            '25th': float(np.percentile(areas_array, 25)),
            '50th': float(np.percentile(areas_array, 50)),
            '75th': float(np.percentile(areas_array, 75)),
            '90th': float(np.percentile(areas_array, 90)),
        }
    }

    return stats


def run_panalesis_subprocess(map_path, min_area_m2):
    """Call this same script as a subprocess passing parameters"""
    try:
        proc = subprocess.run(
            [sys.executable, sys.argv[0], "worker", map_path, str(min_area_m2)],
            capture_output=True, text=True, timeout=1800
        )
        if proc.returncode != 0:
            stderr_content = proc.stderr.strip()
            stdout_content = proc.stdout.strip()
            print(f"Subprocess failed for {map_path}")
            print(f"Return code: {proc.returncode}")
            if stderr_content:
                print(f"STDERR: {stderr_content}")
            if stdout_content:
                print(f"STDOUT: {stdout_content}")
            return None

        if not proc.stdout.strip():
            print(f"No output received from subprocess for {map_path}")
            return None
        output_lines = proc.stdout.strip().split('\n')
        json_line = None
        for line in output_lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break

        if json_line is None:
            print(f"No valid JSON line found in output for {map_path}")
            print(f"Raw output: {proc.stdout}")
            return None

        try:
            return json.loads(json_line)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON output for {map_path}: {e}")
            print(f"Cleaned JSON line: {json_line}")
            return None

    except subprocess.TimeoutExpired:
        print(f"Subprocess timeout for {map_path}")
        return None
    except Exception as e:
        print(f"Subprocess execution error for {map_path}: {e}")
        return None


def downsample_data_if_needed(data, max_dimension=10000, downsample_factor=2):
    """Downsample data if it's too large to prevent memory issues"""
    if len(data.shape) == 3:
        height, width = data.shape[1], data.shape[2]
    else:
        height, width = data.shape[0], data.shape[1]
    if height > max_dimension or width > max_dimension:
        scale_factor = 1.0 / downsample_factor
        print(f"Data is large ({height}x{width}). Downsampling by factor of {downsample_factor}", file=sys.stderr)

        if len(data.shape) == 3:
            data_downsampled = rescale(data, (1, scale_factor, scale_factor),
                                       anti_aliasing=True, channel_axis=0, preserve_range=True)
        else:
            data_downsampled = rescale(data, scale_factor,
                                       anti_aliasing=True, preserve_range=True)
        return data_downsampled.astype(data.dtype)

    return data


def process_single_panalesis_map(map_path, min_area_m2):
    """Process a single panalesis map with proper error handling and memory cleanup"""
    data = None
    dem = None
    fdir = None
    acc = None
    coastlines = None
    continents = None
    full_coastlines = None
    grid = None

    try:
        print(f"Processing map: {map_path}", file=sys.stderr)
        if not os.path.exists(map_path):
            raise FileNotFoundError(f"Map file not found: {map_path}")

        with rasterio.open(map_path) as src:
            data = src.read()
            metadata = src.meta
            print(f"Loaded raster with shape: {data.shape}", file=sys.stderr)
        data = downsample_data_if_needed(data, max_dimension=10000, downsample_factor=2)
        transform = metadata['transform']

        grid = Grid.from_raster(map_path)
        dem = grid.read_raster(map_path)

        dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
        fdir = get_flow_direction(grid, dem, dirmap)
        acc = grid.accumulation(fdir, dirmap=dirmap, nodata_out=np.int64(0))

        full_coastlines = create_contours(data, transform)
        coastlines = full_coastlines.simplify(tolerance=20000, preserve_topology=True)
        continents = filter_large_polygons(coastlines, min_area_m2)
        catchment_areas = get_catchment_areas_by_geometry(grid, continents, acc, fdir, dirmap)

        if not catchment_areas:
            print("No catchment areas found", file=sys.stderr)
            return None

        print(f"Found {len(catchment_areas)} catchment areas", file=sys.stderr)
        statistics = compute_catchment_statistics(catchment_areas)
        age = get_panalesis_age(map_path)

        result = {
            'age': float(age),
            'mean': statistics['mean'],
            'median': statistics['median'],
            'std_dev': statistics['std_dev'],
            'skewness': statistics['skewness']
        }

        print("Processing completed successfully", file=sys.stderr)
        return result

    except Exception as e:
        print(f"Exception processing {map_path}: {str(e)}", file=sys.stderr)
        print("Full traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

    finally:
        try:
            if data is not None:
                del data
            if dem is not None:
                del dem
            if fdir is not None:
                del fdir
            if acc is not None:
                del acc
            if coastlines is not None:
                del coastlines
            if continents is not None:
                del continents
            if full_coastlines is not None:
                del full_coastlines
            if grid is not None:
                del grid
            gc.collect()
            print("Cleanup completed", file=sys.stderr)
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}", file=sys.stderr)


def process_drainage_basins(source, version):
    """Main processing function with memory management"""
    min_area_m2 = 7.5e12
    ages = []
    catch_means = []
    catch_medians = []
    catch_stds = []
    catch_skews = []
    check_memory()
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
        data = downsample_data_if_needed(data, max_dimension=10000, downsample_factor=2)
        check_memory()
        try:
            age = 0
            ages.append(age)
            transform = metadata['transform']
            grid = Grid.from_raster(reprojected_raster)
            dem = grid.read_raster(reprojected_raster)
            check_memory()
            dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
            fdir = get_flow_direction(grid, dem, dirmap)
            acc = grid.accumulation(fdir, dirmap=dirmap, nodata_out=np.int64(0))
            check_memory()
            full_coastlines = create_contours(data, transform)
            coastlines = full_coastlines.simplify(tolerance=20000, preserve_topology=True)
            check_memory()
            continents = filter_large_polygons(coastlines, min_area_m2)
            check_memory()
            catchment_areas = get_catchment_areas_by_geometry(grid, continents, acc, fdir, dirmap)
            if catchment_areas:
                plot_histogram(catchment_areas, "Catchment Area (m²)")
                statistics = compute_catchment_statistics(catchment_areas)
                catch_mean = statistics['mean']
                catch_means.append(catch_mean)
                catch_median = statistics['median']
                catch_medians.append(catch_median)
                catch_std = statistics['std_dev']
                catch_stds.append(catch_std)
                catch_skewness = statistics['skewness']
                catch_skews.append(catch_skewness)
        except MemoryError as e:
            print(f"Memory error occurred: {e}")
            print("Try reducing the downsample_factor or max_dimension parameters")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            print("Cleaning up memory...")
            for var_name in ['data', 'dem', 'fdir', 'acc', 'coastlines', 'continents']:
                if var_name in locals():
                    del locals()[var_name]
            gc.collect()
            check_memory()
        combined = list(zip(ages, catch_means, catch_medians, catch_stds, catch_skews))
        combined.sort(key=lambda x: x[0])
        ages, catch_means, catch_medians, catch_stds, catch_skews = zip(*combined)
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        ages, catch_means, catch_medians, catch_stds, catch_skews = [], [], [], [], []
        if len(sys.argv) > 1 and sys.argv[1] == "worker":
            if len(sys.argv) < 4:
                print("Error: Insufficient arguments for worker mode", file=sys.stderr)
                sys.exit(1)
            map_path = sys.argv[2]
            try:
                min_area_m2 = float(sys.argv[3])
            except ValueError as e:
                print(f"Error: Invalid min_area_m2 value: {sys.argv[3]}", file=sys.stderr)
                sys.exit(1)
            stats = process_single_panalesis_map(map_path, min_area_m2)
            if stats:
                print(json.dumps(stats))
            else:
                print(json.dumps({}))

            sys.exit(0)
        total_maps = len(panalesis_maps)
        print(f"Processing {total_maps} panalesis maps...")
        for i, map_path in enumerate(panalesis_maps):
            print(f"Processing map {i + 1}/{total_maps}: {os.path.basename(map_path)}")
            try:
                age = get_panalesis_age(map_path)
                ages.append(age)
                stats = run_panalesis_subprocess(map_path, min_area_m2)
                if stats and stats:
                    catch_means.append(stats.get('mean'))
                    catch_medians.append(stats.get('median'))
                    catch_stds.append(stats.get('std_dev'))
                    catch_skews.append(stats.get('skewness'))
                    print(f"Successfully processed {os.path.basename(map_path)}")
                else:
                    print(f"Failed to process {os.path.basename(map_path)}")
                    catch_means.append(None)
                    catch_medians.append(None)
                    catch_stds.append(None)
                    catch_skews.append(None)
            except Exception as e:
                print(f"Error processing {map_path}: {e}")
                ages.append(None)
                catch_means.append(None)
                catch_medians.append(None)
                catch_stds.append(None)
                catch_skews.append(None)

        valid_data = [(a, m, med, s, sk) for a, m, med, s, sk in
                      zip(ages, catch_means, catch_medians, catch_stds, catch_skews)
                      if a is not None and m is not None]
        if valid_data:
            combined = sorted(valid_data, key=lambda x: x[0])
            ages, catch_means, catch_medians, catch_stds, catch_skews = zip(*combined)
        else:
            print("No valid data processed!")
            return None
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")
        return None

    df = pd.DataFrame({
        'Age': ages,
        'Mean_Catchment_Area': catch_means,
        'Median_Catchment_Area': catch_medians,
        'Std-Dev_Catchment_Area': catch_stds,
        'Skewness_Catchment': catch_skews
    })
    stat_out(df, join_on='Age', version=version, source=source)


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    try:
        process_drainage_basins(source, version)
    except Exception as e:
        print(f"Processing failed with error: {e}")