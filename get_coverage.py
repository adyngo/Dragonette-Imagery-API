from pystac import Catalog, Item, Collection
import geopandas as gpd
import folium
import requests
from urllib.parse import urlparse
import os

# Load the root catalog
catalog_url = "https://wyvern-prod-public-open-data-program.s3.ca-central-1.amazonaws.com/catalog.json"
catalog = Catalog.from_file(catalog_url)

# Function to recursively get all items from the catalog
def get_all_items(catalog):
    items = []
    print(f"Processing {catalog.id} ({catalog.STAC_OBJECT_TYPE})")
    
    # Process child catalogs/collections
    for child_link in catalog.get_child_links():
        print(f"Processing child {child_link.href}")
        child = catalog.get_single_link("child").resolve_stac_object(root=catalog).target
        if isinstance(child, (Catalog, Collection)):
            items.extend(get_all_items(child))
    
    # Process items directly in this catalog
    for item_link in catalog.get_item_links():
        try:
            item = item_link.resolve_stac_object(root=catalog).target
            if isinstance(item, Item):
                items.append(item)
        except Exception as e:
            print(f"Error loading item {item_link.href}: {str(e)}")
    
    return items

print("Loading catalog items...")
all_items = get_all_items(catalog)

if not all_items:
    raise Exception("No items found in the catalog. Possible reasons:\n"
                    "1. Catalog structure is different than expected\n"
                    "2. Items are in protected collections\n"
                    "3. Network restrictions prevent access")

print(f"Found {len(all_items)} items")

# Create GeoDataFrame from item geometries
gdf = gpd.GeoDataFrame.from_features([
    {
        "type": "Feature",
        "geometry": item.geometry,
        "properties": {
            "id": item.id,
            "datetime": item.datetime.isoformat() if item.datetime else None,
            "collection": item.collection_id
        }
    }
    for item in all_items
])

# Create a world map centered at (0,0)
m = folium.Map(location=[0, 0], zoom_start=2)

# Add all footprints to the map
for _, row in gdf.iterrows():
    folium.GeoJson(
        row.geometry,
        tooltip=f"""
        <b>ID:</b> {row['id']}<br>
        <b>Date:</b> {row['datetime']}<br>
        <b>Collection:</b> {row['collection']}
        """
    ).add_to(m)

# Save the map
output_dir = "Dragonette-Imagery-API/result"
os.makedirs(output_dir, exist_ok=True)
m.save(f"{output_dir}/wyvern_data_coverage.html")
print(f"Map saved to {output_dir}/wyvern_data_coverage.html")
