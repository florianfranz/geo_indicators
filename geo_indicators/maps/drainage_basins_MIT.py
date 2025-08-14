import os
import geojson
import geopandas as gpd
import gc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pysheds.grid import Grid
import rasterio
from rasterio.features import rasterize
from rasterio.transform import xy, rowcol
from scipy.spatial import cKDTree
from skimage import measure
from shapely.geometry import Polygon, shape
from shapely.errors import GEOSException
from shapely.ops import unary_union
from pyproj import Transformer
import xarray as xr
from geo_indicators.maps.coastal_length import close_contour
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_reproj_MITgcm_nodes,
    get_out_dir_path,
    get_panalesis_maps,
    get_panalesis_age,
    get_flow_paths,
    get_temperatures_map
)

def safe_buffer_zero(geom):
    try:
        return geom.buffer(0)
    except GEOSException:
        return None


def trace_clipped_flow_path(clipped_fdir, start_coord, transform):
    start_row, start_col = rowcol(transform, *start_coord)
    dirmap = {
        1: (0, 1),  # East
        2: (1, 1),  # Southeast
        4: (1, 0),  # South
        8: (1, -1),  # Southwest
        16: (0, -1),  # West
        32: (-1, -1),  # Northwest
        64: (-1, 0),  # North
        128: (-1, 1)  # Northeast
    }
    path = [(start_row, start_col)]
    current_row, current_col = start_row, start_col
    while True:
        flow_dir = clipped_fdir[current_row, current_col]
        if np.isnan(flow_dir) or flow_dir not in dirmap:
            break
        step = dirmap[flow_dir]
        next_row, next_col = current_row + step[0], current_col + step[1]
        if (next_row < 0 or next_row >= clipped_fdir.shape[0] or
                next_col < 0 or next_col >= clipped_fdir.shape[1]):
            break
        path.append((next_row, next_col))
        current_row, current_col = next_row, next_col
    return path

def get_catchment_area(source,version,age,band,metadata):
    contour_levels = [0, -2000]
    polygons = []
    raster_crs = metadata['crs']
    transform = metadata['transform']
    reproj_MITgcm_nodes_path = get_reproj_MITgcm_nodes()
    gdf_points = gpd.read_file(reproj_MITgcm_nodes_path)
    esri_54034_crs = gdf_points.crs
    out_dir_path = get_out_dir_path(source, version)
    filled_raster_path = os.path.join(out_dir_path, f"{source}_{version}",f"{source}_{version}_{age}_filled.tif")
    out_reproj_MITgcm_nodes_path = os.path.join(out_dir_path, f"{source}_{version}", f"out_MITgcm_nodes_{age}.geojson")
    start_end_geojson_path = os.path.join(out_dir_path, f"{source}_{version}", f"start_end_points_{age}.geojson")
    flow_paths_geojson_path = os.path.join(out_dir_path, f"{source}_{version}", f"flow_paths_{age}.geojson")
    for level in contour_levels:
        contours = measure.find_contours(band, level)
        for contour in contours:
            transformed_contour = []
            for point in contour:
                x, y = transform * (point[1], point[0])
                transformed_contour.append((x, y))

            closed_contour = close_contour(transformed_contour)
            if closed_contour:
                polygon = Polygon(closed_contour)
                if polygon.is_valid:
                    polygons.append({'geometry': polygon, 'level': level})

    gdf = gpd.GeoDataFrame(polygons)
    gdf.set_crs(raster_crs, allow_override=True)
    level_0_polygons = gdf[gdf['level'] == 0]
    nested_polygons = []
    for _, parent_row in level_0_polygons.iterrows():
        parent_polygon = parent_row['geometry']
        for _, child_row in gdf.iterrows():
            child_polygon = child_row['geometry']
            child_level = child_row['level']
            if parent_polygon.contains(child_polygon) and not parent_polygon.equals(child_polygon):
                nested_polygons.append({'geometry': child_polygon, 'level': child_level})
    nested_gdf = gpd.GeoDataFrame(nested_polygons)
    nested_gdf.set_crs(gdf.crs, inplace=True)
    nested_with_flag = []
    for _, parent_row in nested_gdf.iterrows():
        parent_polygon = parent_row['geometry']
        parent_level = parent_row['level']
        parent_flag = 0
        if parent_level == 0:
            for _, child_row in nested_gdf.iterrows():
                child_polygon = child_row['geometry']
                child_level = child_row['level']
                if parent_polygon.contains(child_polygon) and child_level == -2000:
                    parent_flag = 1
            nested_with_flag.append({
                'geometry': parent_polygon,
                'level': parent_level,
                'FLAG': parent_flag
            })
    nested_with_flag_gdf = gpd.GeoDataFrame(nested_with_flag)
    nested_with_flag_gdf.set_crs(nested_gdf.crs, inplace=True)
    nested_flag_1_gdf = nested_with_flag_gdf[nested_with_flag_gdf['FLAG'] == 1]
    level_0_contours_gdf = gdf[gdf['level'] == 0]
    diff_polygons = []
    for _, contour_row in level_0_contours_gdf.iterrows():
        contour_polygon = contour_row['geometry']
        result_polygon = contour_polygon
        for _, nested_row in nested_flag_1_gdf.iterrows():
            nested_polygon = nested_row['geometry']
            result_polygon = result_polygon.difference(nested_polygon)
        if result_polygon.is_valid and not result_polygon.is_empty:
            diff_polygons.append({'geometry': result_polygon, 'level': contour_row['level']})
    diff_gdf = gpd.GeoDataFrame(diff_polygons)
    diff_gdf.set_crs(gdf.crs, inplace=True)
    dissolved_geometry = unary_union(diff_gdf.geometry)
    dissolved_gdf = gpd.GeoDataFrame(geometry=[dissolved_geometry], crs=diff_gdf.crs)
    gdf_polygons = dissolved_gdf
    dissolved_polygon = gdf_polygons.geometry.union_all()
    gdf_points['CONT'] = gdf_points.geometry.apply(
        lambda point: 1 if dissolved_polygon.contains(point) else 0).astype(int)

    polygons = nested_with_flag_gdf
    polygons = polygons[polygons['FLAG'] == 0]

    if polygons.crs is None:
        polygons = polygons.set_crs(metadata['crs'])

    if polygons.crs != metadata['crs']:
        polygons = polygons.to_crs(metadata['crs'])

    polygons['geometry'] = polygons['geometry'].apply(safe_buffer_zero)

    polygons = polygons.dropna(subset=['geometry'])
    polygons = polygons[polygons.is_valid & ~polygons.is_empty]

    buffered_polygons = polygons.copy()
    buffered_polygons['geometry'] = buffered_polygons['geometry'].apply(
        lambda geom: geom.buffer(25) if geom.is_valid else None
    )

    buffered_polygons = buffered_polygons.dropna(subset=['geometry'])
    buffered_polygons = buffered_polygons[buffered_polygons.is_valid & ~buffered_polygons.is_empty]

    polygon_mask = rasterize(
        [(geom, 1) for geom in buffered_polygons.geometry],
        out_shape=band.shape,
        transform=metadata['transform'],
        fill=0,
        dtype='uint8'
    )

    new_value = 444
    band[polygon_mask == 1] = new_value
    os.makedirs(os.path.dirname(filled_raster_path), exist_ok=True)
    with rasterio.open(filled_raster_path, 'w', **metadata) as dst:
        dst.write(band, 1)
    grid = Grid.from_raster(filled_raster_path)
    dem = grid.read_raster(filled_raster_path)

    pit_filled_dem = grid.fill_pits(dem, epsilon=1e-3)
    flooded_dem = grid.fill_depressions(pit_filled_dem, epsilon=1e-3)
    inflated_dem = grid.resolve_flats(flooded_dem)
    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap, nodata_out=np.int64(0))
    with rasterio.open(filled_raster_path) as src:
        original_dem = src.read(1)
        transform = src.transform
    valid_mask = original_dem > 0
    clipped_fdir = np.where(valid_mask, fdir, np.nan)
    ocean_gdf = gdf_points[gdf_points['CONT'] == 0]
    ocean_coords = np.array([[geom.x, geom.y] for geom in ocean_gdf.geometry])
    ocean_ids = ocean_gdf['ID'].to_numpy()

    ocean_points = np.column_stack((ocean_coords, ocean_ids))

    tree = cKDTree(ocean_coords)
    geojson_features = []
    start_end_features = []
    out_ids = []

    gdf_points["TYPE"] = "Other"

    gdf_points.loc[gdf_points["CONT"] == 1, "TYPE"] = "Start"

    used_ocean_ids = set()

    for idx, row in gdf_points.iterrows():
        if row['CONT'] == 1:
            start_point = (row.geometry.x, row.geometry.y)
            flow_path = trace_clipped_flow_path(clipped_fdir, start_point, transform)
            flow_path_coords = [xy(transform, r, c) for r, c in flow_path]
            last_point_coords = flow_path_coords[-1] if flow_path_coords else start_point
            _, nearest_idx = tree.query(last_point_coords)  # Find nearest ocean point
            nearest_id = ocean_points[nearest_idx, 2]
            used_ocean_ids.add(nearest_id)
            out_ids.append(nearest_id)
            if flow_path_coords and len(flow_path_coords) >= 2:
                geojson_features.append(geojson.Feature(
                    geometry=geojson.LineString(flow_path_coords),
                    properties={'ID': row['ID'], 'OUT_ID': nearest_id}
                ))
            start_end_features.append(geojson.Feature(
                geometry=geojson.Point(start_point),
                properties={'Type': 'Start', 'ID': row['ID'], 'OUT_ID': nearest_id}
            ))
            start_end_features.append(geojson.Feature(
                geometry=geojson.Point(last_point_coords),
                properties={'Type': 'End', 'ID': row['ID'], 'OUT_ID': nearest_id}
            ))
            gdf_points.loc[gdf_points["ID"] == nearest_id, "FLOW_END_X"] = last_point_coords[0]
            gdf_points.loc[gdf_points["ID"] == nearest_id, "FLOW_END_Y"] = last_point_coords[1]
        else:
            out_ids.append(row['ID'])

    gdf_points['OUT_ID'] = out_ids
    gdf_points.loc[gdf_points["ID"].isin(used_ocean_ids), "TYPE"] = "End"
    os.makedirs(os.path.dirname(out_reproj_MITgcm_nodes_path), exist_ok=True)
    gdf_points.to_file(out_reproj_MITgcm_nodes_path)

    flows_gdf = gpd.GeoDataFrame(
        [feature['properties'] for feature in geojson_features],
        geometry=[shape(feature['geometry']) for feature in geojson_features],
        crs=raster_crs)
    flows_gdf.to_file(flow_paths_geojson_path)

    cell_width = abs(grid.affine.a)
    cell_height = abs(grid.affine.e)
    cell_area = cell_width * cell_height
    xmin, ymin, xmax, ymax = grid.bbox
    buffer_x = 2 * cell_width
    buffer_y = 2 * cell_height

    acc = grid.accumulation(fdir, dirmap=dirmap, nodata_out=np.int64(0))
    threshold = 100

    outlets = gdf_points[gdf_points['TYPE'] == 'End']
    outlets = outlets.reset_index()

    catchment_stats = []

    transformer = Transformer.from_crs("ESRI:54034", "EPSG:4326", always_xy=True)
    var_name = "puma_temperature_surface_air"
    netcdf_path = get_temperatures_map()

    for i, row in outlets.iterrows():
        idx = row['index']
        x = row["FLOW_END_X"]
        y = row["FLOW_END_Y"]

        if (
                x <= xmin + buffer_x or x >= xmax - buffer_x or
                y <= ymin + buffer_y or y >= ymax - buffer_y
        ):
            print("case 1: all nan because flow end is outside bounds")
            catchment_stats.append({
                'index': idx,
                'area': np.nan,
                'max_elevation': np.nan,
                'mean_temperature': np.nan
            })
            continue
        try:
            x_snap, y_snap = grid.snap_to_mask(acc > threshold, (x, y))
            if (
                    x_snap <= xmin + buffer_x or x_snap >= xmax - buffer_x or
                    y_snap <= ymin + buffer_y or y_snap >= ymax - buffer_y
            ):
                print("case 2: all nan because flow end snapped point is outside bounds")
                catchment_stats.append({
                    'index': idx,
                    'area': np.nan,
                    'max_elevation': np.nan,
                    'mean_temperature': np.nan
                })
                continue

            catch = grid.catchment(
                x=x_snap, y=y_snap,
                fdir=fdir, dirmap=dirmap,
                xytype='coordinate'
            )
            catch_array = catch.view()
            contours = measure.find_contours(catch_array, level=0.5)
            contours_wgs84 = []
            for contour in contours:
                projected_coords = [grid.affine * (c[1], c[0]) for c in contour]

                wgs84_coords = [transformer.transform(x, y) for x, y in projected_coords]
                contours_wgs84.append(wgs84_coords)

            lon_end, lat_end = transformer.transform(x, y)
            lon_snap, lat_snap = transformer.transform(x_snap,y_snap)

            fig, ax = plt.subplots()
            centroids = []
            for contour in contours_wgs84:
                lons, lats = zip(*contour)
                ax.plot(lons, lats, 'b-')
                polygon = Polygon(contour)
                centroid = polygon.centroid

                centroid_lon = centroid.x
                centroid_lat = centroid.y
                print(centroid_lon,centroid_lat)
                ax.plot(centroid_lon,centroid_lat,'bo',label='Catchment Centroid')
                centroids.append((centroid_lon, centroid_lat))
            ax.plot(lon_snap, lat_snap, 'go', label='Catchment End Point')
            ax.plot(lon_end, lat_end, 'ro', label='Nearest MITgcm Outlet')
            ax.set_xlabel('Longitude [°]')
            ax.set_ylabel('Latitude [°]')
            ax.legend()
            plt.show()

            ds = xr.open_dataset(netcdf_path)
            temperature = ds[var_name]

            sampled_temperatures = []
            for lon, lat in centroids:
                temp = temperature.sel(latitude=lat, longitude=lon, method="nearest").values.item()
                sampled_temperatures.append(temp)

            mean_temperature = np.mean(sampled_temperatures)

            masked_dem = np.where(catch.view(), dem, np.nan)
            max_elevation = np.nanmax(masked_dem)
            num_cells = np.count_nonzero(catch_array)
            catchment_area = num_cells * cell_area
            print("Case 3: Able to calculate catchment statistics")
            catchment_stats.append({
                'index': idx,
                'area': catchment_area,
                'max_elevation': max_elevation,
                'mean_temperature': mean_temperature
            })
            del catch, catch_array
            gc.collect()
        except Exception as e:
            print("case 4: all nan because error")
            print(e)
            catchment_stats.append({
                'index': idx,
                'area': np.nan,
                'max_elevation': np.nan,
                'mean_temperature': np.nan
            })
            continue
    catchment_df = pd.DataFrame(catchment_stats).set_index('index')
    area_series = catchment_df['area']
    max_elev_series = catchment_df['max_elevation']
    mean_temp_series = catchment_df['mean_temperature']
    gdf_points['catchment_area'] = gdf_points.index.map(area_series)
    gdf_points['max_elevation'] = gdf_points.index.map(max_elev_series)
    gdf_points['mean_temperature'] = gdf_points.index.map(mean_temp_series)

    gdf_points.to_file(out_reproj_MITgcm_nodes_path)

    return catchment_stats

def reproj_flow_paths(source,version):
    if source == "ETOPO":
        if version != "2022":
            version = "2022"
    flow_paths = get_flow_paths(source,version)
    for flow_path in flow_paths:
        flows_gdf = gpd.read_file(flow_path)
        flows_gdf = flows_gdf.set_crs("ESRI:54034", allow_override=True)
        flows_gdf.to_file(flow_path)


def process_drainage_basins_MITgcm(source, version):
    ages = []
    if source == "ETOPO":
        if version != "2022":
            version = "2022"
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        band = data[0]
        age = 0
        ages.append(age)
        catchment_stats = get_catchment_area(source,version,age,band,metadata)
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            if age < 100:
                ages.append(age)
                data, metadata = load_tiff(map)
                band = data[0]
                catchment_stats = get_catchment_area(source, version, age, band, metadata)


    return catchment_stats



if __name__ == "__main__":
    source = "ETOPO"
    version = "2022"
    catchment_stats = process_drainage_basins_MITgcm(source, version)
    reproj_flow_paths(source, version)

