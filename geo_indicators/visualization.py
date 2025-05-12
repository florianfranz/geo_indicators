import matplotlib.pyplot as plt


def plot_mask(mask, title):
    plt.figure(figsize=(10, 6))
    plt.imshow(mask, cmap='Greys', interpolation='none')
    plt.title(title)
    plt.xlabel("X (pixel index)")
    plt.ylabel("Y (pixel index)")
    plt.tight_layout()
    plt.show()