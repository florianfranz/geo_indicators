import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from geo_indicators.utils import get_output_csv_path

def plot_mask(mask, title):
    plt.figure(figsize=(10, 6))
    plt.imshow(mask, cmap='Greys', interpolation='none')
    plt.title(title)
    plt.xlabel("Longitude (meters)")
    plt.ylabel("Latitude (meters)")
    plt.tight_layout()
    plt.show()


def plot_passage(mask, routes):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(mask, cmap='Blues', origin='lower')  # Sea=0, Land=1
    for route in routes:
        x_coords = range(len(route))
        y_coords = [step.center for step in route]
        ax.plot(x_coords, y_coords, color='red', linewidth=2)

    plt.xlabel('Longitude (meters)')
    plt.ylabel('Latitude (meters)')
    plt.title('Best Ocean Passage (Red)')
    plt.grid(True)
    plt.show()


def plot_gdf_simple(gdf, title):
    gdf.plot(edgecolor='black', facecolor='none', linewidth=0.5)
    plt.title(title)
    plt.xlabel("Longitude (meters)")
    plt.ylabel("Latitude (meters)")
    plt.show()


def plot_timeseries_simple(ages, metric, metric_name, title):
    plt.figure(figsize=(10, 6))
    plt.plot(ages, metric, marker='o', linestyle='-', color='blue')
    plt.xlabel('Age (Ma)')
    plt.ylabel(metric_name)
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_timeseries_double(ages, metric1, metric1_name, metric2, metric2_name, title):
    plt.figure(figsize=(10, 6))
    plt.plot(ages, metric1, marker='o', linestyle='-', color='blue', label=metric1_name)
    plt.plot(ages, metric2, marker='o', linestyle='-', color='red', label=metric2_name)
    plt.xlabel('Age (Ma)')
    plt.ylabel('Area (m²)')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def heatmap_chart(source, version):
    df_path = get_output_csv_path(source, version)
    df = pd.read_csv(df_path)

    plt.figure(figsize=(12, 8))
    heatmap = sns.heatmap(df.drop('Age', axis=1).corr(), annot=True, cmap='coolwarm', linewidths=0.5)

    # Adjust label rotation and font size
    heatmap.set_xticklabels(heatmap.get_xticklabels(), rotation=45, horizontalalignment='right', fontsize=10)
    heatmap.set_yticklabels(heatmap.get_yticklabels(), rotation=0, fontsize=10)

    plt.tight_layout()  # Adjust layout to ensure everything fits within the plot area
    plt.show()

def radar_chart(source,version):
    df_path = get_output_csv_path(source, version)
    df = pd.read_csv(df_path)
    area_columns = [
    'Land_Area', 'Polar_Land_Area', 'Temperate_Land_Area', 'Subtropical_Land_Area',
    'Tropical_Land_Area', 'Northern_Land_Area', 'Southern_Land_Area', 'High_Altitude_Area',
    'Continental_Shelves_Area'
    ]
    num_vars = len(area_columns)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    for i, row in df.iterrows():
        values = row[area_columns].tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=1, linestyle='solid', label=f'Age {row["Age"]}')
        ax.fill(angles, values, alpha=0.25)

    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(area_columns)
    plt.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1))
    plt.show()







