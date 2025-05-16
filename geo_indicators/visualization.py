import matplotlib.pyplot as plt


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
