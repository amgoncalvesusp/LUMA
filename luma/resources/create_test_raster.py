"""Generate a realistic synthetic test raster for LUMA.

Creates a GeoTIFF with ESA WorldCover classes covering Araraquara-SP, Brazil.
Run this script once to generate the test file:

    python -m luma.resources.create_test_raster

The output is saved to: luma/resources/test_esa_worldcover_araraquara.tif
"""

import numpy as np

# Test area: Araraquara, SP, Brazil (UNIARA campus vicinity)
# ~20km x 20km area
CENTER_LAT = -21.7845
CENTER_LON = -48.1780
HALF_DEG = 0.10  # ~10km in each direction

WEST = CENTER_LON - HALF_DEG
EAST = CENTER_LON + HALF_DEG
SOUTH = CENTER_LAT - HALF_DEG
NORTH = CENTER_LAT + HALF_DEG

# ESA WorldCover classes
TREE_COVER = 10
SHRUBLAND = 20
GRASSLAND = 30
CROPLAND = 40
BUILT_UP = 50
BARE = 60
WATER = 80
WETLAND = 90

# 10m resolution equivalent: ~670x670 pixels for 0.2 deg
WIDTH = 670
HEIGHT = 670


def generate() -> str:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    from scipy.ndimage import uniform_filter, gaussian_filter
    from pathlib import Path

    np.random.seed(2024)

    # Create base noise layers for each class "affinity"
    tree_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=40)
    crop_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=50)
    urban_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=25)
    water_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=60)

    # Add an urban center (Araraquara city core)
    cy, cx = HEIGHT // 2, WIDTH // 2
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    dist_from_center = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    urban_affinity += np.exp(-dist_from_center ** 2 / (80 ** 2)) * 3

    # Add a river-like feature (diagonal) — narrow core for water
    river_dist = np.abs((yy - cy) * 0.7 + (xx - cx) * 0.3) / np.sqrt(0.7**2 + 0.3**2)
    water_affinity += np.exp(-river_dist ** 2 / (5 ** 2)) * 6

    # Add a small lake in the southeast
    lake_dist = np.sqrt((yy - HEIGHT * 0.7) ** 2 + (xx - WIDTH * 0.75) ** 2)
    water_affinity += np.exp(-lake_dist ** 2 / (25 ** 2)) * 5

    # Add cropland in the periphery
    crop_affinity += np.exp(-(-dist_from_center + 250) ** 2 / (120 ** 2)) * 2

    # Add tree cover in the north/northeast quadrant (forest remnants)
    tree_zone = np.exp(-((yy - HEIGHT * 0.25) ** 2 / (150 ** 2) + (xx - WIDTH * 0.7) ** 2 / (150 ** 2))) * 3
    tree_affinity += tree_zone
    # Add another forest patch in the south
    tree_zone2 = np.exp(-((yy - HEIGHT * 0.8) ** 2 / (100 ** 2) + (xx - WIDTH * 0.3) ** 2 / (120 ** 2))) * 2.5
    tree_affinity += tree_zone2

    # Add shrubland zones (transition areas between forest and cropland)
    shrub_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=35)
    shrub_zone = np.exp(-((yy - HEIGHT * 0.4) ** 2 / (120 ** 2) + (xx - WIDTH * 0.15) ** 2 / (100 ** 2))) * 3
    shrub_affinity += shrub_zone

    # Add grassland patches (scattered pasture)
    grass_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=30)
    grass_zone1 = np.exp(-((yy - HEIGHT * 0.65) ** 2 / (100 ** 2) + (xx - WIDTH * 0.65) ** 2 / (100 ** 2))) * 3
    grass_zone2 = np.exp(-((yy - HEIGHT * 0.15) ** 2 / (80 ** 2) + (xx - WIDTH * 0.4) ** 2 / (80 ** 2))) * 2.5
    grass_affinity += grass_zone1 + grass_zone2

    # Add bare/exposed soil near urban fringe
    bare_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=20)
    bare_zone = np.exp(-((yy - HEIGHT * 0.55) ** 2 / (60 ** 2) + (xx - WIDTH * 0.55) ** 2 / (60 ** 2))) * 2.5
    bare_affinity += bare_zone

    # Add wetland along river margins (wider than river but weaker)
    wetland_affinity = gaussian_filter(np.random.randn(HEIGHT, WIDTH), sigma=20)
    wetland_zone = np.exp(-river_dist ** 2 / (25 ** 2)) * 2.5
    wetland_affinity += wetland_zone

    # Stack affinities and assign class by maximum
    affinities = {
        TREE_COVER: tree_affinity + 0.8,
        CROPLAND: crop_affinity + 0.2,
        BUILT_UP: urban_affinity + 0.3,
        GRASSLAND: grass_affinity + 0.7,
        SHRUBLAND: shrub_affinity + 0.5,
        WATER: water_affinity + 0.2,
        WETLAND: wetland_affinity - 0.2,
        BARE: bare_affinity + 0.2,
    }

    # Choose class with highest affinity per pixel
    class_ids = list(affinities.keys())
    stack = np.stack([affinities[c] for c in class_ids], axis=0)
    winner = np.argmax(stack, axis=0)
    data = np.array([class_ids[w] for w in winner.ravel()], dtype=np.uint8).reshape(HEIGHT, WIDTH)

    # Statistics
    unique, counts = np.unique(data, return_counts=True)
    total = data.size
    print("Generated land cover distribution:")
    class_names = {
        10: "Tree Cover", 20: "Shrubland", 30: "Grassland",
        40: "Cropland", 50: "Built-up", 60: "Bare",
        80: "Water", 90: "Wetland",
    }
    for cls, cnt in zip(unique, counts):
        pct = cnt / total * 100
        print(f"  {class_names.get(cls, f'Class {cls}'):15s}: {pct:5.1f}%")

    # Write GeoTIFF
    transform = from_bounds(WEST, SOUTH, EAST, NORTH, WIDTH, HEIGHT)
    out_path = Path(__file__).parent / "test_esa_worldcover_araraquara.tif"

    with rasterio.open(
        str(out_path), "w", driver="GTiff",
        height=HEIGHT, width=WIDTH, count=1,
        dtype="uint8", crs=CRS.from_epsg(4326),
        transform=transform, nodata=0,
        compress="lzw",
    ) as dst:
        dst.write(data, 1)

    print(f"\nSaved to: {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
    print(f"Extent: [{WEST:.4f}, {SOUTH:.4f}] to [{EAST:.4f}, {NORTH:.4f}]")
    print(f"Suggested test: lat={CENTER_LAT}, lon={CENTER_LON}, radius=5000m")
    return str(out_path)


def generate_temporal() -> str:
    """Generate a second raster by perturbing the first one (simulating land cover change).

    ~15% of pixels change to simulate realistic change between two dates:
    - Tree Cover -> Cropland (deforestation for agriculture)
    - Grassland/Shrubland -> Cropland (agricultural expansion)
    - edges of Built-up -> expanded Built-up (urban growth)
    - some Cropland -> Built-up (periurban conversion)
    """
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    from scipy.ndimage import gaussian_filter
    from pathlib import Path

    # Load the original t1 raster
    t1_path = Path(__file__).parent / "test_esa_worldcover_araraquara.tif"
    with rasterio.open(str(t1_path)) as src:
        data = src.read(1).copy()
        profile = src.profile.copy()

    np.random.seed(42)

    cy, cx = HEIGHT // 2, WIDTH // 2
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    dist_from_center = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)

    # Change probability map: higher near city edges and forest margins
    change_prob = np.zeros((HEIGHT, WIDTH), dtype=float)

    # Urban expansion ring (just outside current city)
    urban_ring = np.exp(-((dist_from_center - 100) ** 2) / (50 ** 2)) * 0.4
    change_prob += urban_ring

    # Deforestation pressure in the NE forest remnant
    deforest_zone = np.exp(-((yy - HEIGHT * 0.25) ** 2 / (100 ** 2) + (xx - WIDTH * 0.7) ** 2 / (100 ** 2))) * 0.35
    change_prob += deforest_zone

    # Agricultural expansion near existing cropland-forest boundary
    ag_expand = gaussian_filter(np.random.rand(HEIGHT, WIDTH), sigma=30) * 0.08
    change_prob += ag_expand

    # Decide which pixels change
    random_field = np.random.rand(HEIGHT, WIDTH)
    changes = random_field < change_prob

    # Apply changes based on current class
    new_data = data.copy()

    # Tree Cover -> Cropland (deforestation)
    mask = changes & (data == TREE_COVER)
    new_data[mask] = CROPLAND

    # Shrubland -> Cropland (cleared for agriculture)
    mask = changes & (data == SHRUBLAND)
    new_data[mask] = CROPLAND

    # Grassland near city -> Built-up
    urban_nearby = dist_from_center < 150
    mask = changes & (data == GRASSLAND) & urban_nearby
    new_data[mask] = BUILT_UP

    # Cropland near city -> Built-up (periurban)
    mask = changes & (data == CROPLAND) & (dist_from_center < 100)
    new_data[mask] = BUILT_UP

    # Bare -> Built-up (construction on bare land)
    mask = changes & (data == BARE)
    new_data[mask] = BUILT_UP

    # Statistics
    unique, counts = np.unique(new_data, return_counts=True)
    total = new_data.size
    class_names = {
        10: "Tree Cover", 20: "Shrubland", 30: "Grassland",
        40: "Cropland", 50: "Built-up", 60: "Bare",
        80: "Water", 90: "Wetland",
    }
    changed_pct = np.sum(new_data != data) / total * 100
    print(f"\nGenerated TEMPORAL raster ({changed_pct:.1f}% pixels changed):")
    for cls, cnt in zip(unique, counts):
        pct = cnt / total * 100
        print(f"  {class_names.get(cls, f'Class {cls}'):15s}: {pct:5.1f}%")

    out_path = Path(__file__).parent / "test_esa_worldcover_araraquara_t2.tif"
    with rasterio.open(str(out_path), "w", **profile) as dst:
        dst.write(new_data, 1)

    print(f"Saved to: {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
    return str(out_path)


if __name__ == "__main__":
    generate()
    generate_temporal()
