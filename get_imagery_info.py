from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pystac import Catalog, Item, Collection    
import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np
import os

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

def get_spectral_info(item):
    """Extract spectral band information from an item's assets"""
    bands = []
    for asset_key, asset in item.assets.items():
        if 'eo:bands' in asset.extra_fields:
            for band in asset.extra_fields['eo:bands']:
                band_info = {
                    'name': band.get('name', 'N/A'),
                    'common_name': band.get('common_name', 'N/A'),
                    'center_wavelength': band.get('center_wavelength', 'N/A'),
                    'asset': asset_key
                }
                bands.append(band_info)
        elif 'raster:bands' in asset.extra_fields:
            for band in asset.extra_fields['raster:bands']:
                band_info = {
                    'name': band.get('name', 'N/A'),
                    'common_name': band.get('common_name', 'N/A'),
                    'center_wavelength': band.get('center_wavelength', 'N/A'),
                    'asset': asset_key
                }
                bands.append(band_info)
    return bands

def create_spectral_chart(bands, item_id):
    """Create matplotlib spectral profile plot with vertical labels"""
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # Extract valid wavelengths
    wavelengths = []
    band_names = []
    for band in bands:
        if isinstance(band['center_wavelength'], (int, float)):
            wavelengths.append(band['center_wavelength'])
            band_names.append(f"{band['name']}\n({band['common_name']})")

    if not wavelengths:
        return None

    # Create spectral profile
    ax.vlines(wavelengths, 0, 1, colors='blue', linewidth=2)
    ax.set_xticks(wavelengths)
    ax.set_xticklabels(band_names, rotation=90, ha='center')
    ax.set_xlabel('Wavelength (nm)', labelpad=15)
    ax.set_yticks([])
    ax.set_title(f"Spectral Profile - {item_id}", pad=20)
    ax.grid(axis='x', alpha=0.3)

    # Save to buffer
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

def create_metadata_table(item):
    """Create a table with imagery metadata"""
    props = item.properties
    data = [
        ['Property', 'Value'],
        ['Acquisition Date', props.get('datetime', 'N/A')],
        ['Cloud Cover', f"{props.get('eo:cloud_cover', 'N/A')}%"],
        ['Resolution', f"{props.get('gsd', 'N/A')} m"],
        ['Sensor', props.get('eo:instrument', 'N/A')],
        ['Platform', props.get('platform', 'N/A')],
        ['Processing Level', props.get('processing:level', 'N/A')]
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), (0.8, 0.8, 0.8)),
        ('TEXTCOLOR', (0,0), (-1,0), (0, 0, 0)),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), (0.95, 0.95, 0.95)),
        ('GRID', (0,0), (-1,-1), 0.5, (0.7, 0.7, 0.7)),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return table

def create_spectral_pdf(items, filename="Dragonette-Imagery-API/result/spectral_report.pdf"):
    """Create PDF with spectral charts and metadata tables"""
    output_dir = os.path.dirname(filename)
    os.makedirs(output_dir, exist_ok=True)
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    elements.append(Paragraph("Satellite Imagery Analysis Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Create sections for each item
    for i, item in enumerate(items):
        bands = get_spectral_info(item)
        chart_buf = create_spectral_chart(bands, item.id)

        if chart_buf:
            elements.append(Paragraph(f"Imagery Analysis: {item.id}", styles['Heading2']))
            elements.append(Spacer(1, 6))
            elements.append(Image(chart_buf, width=500, height=200))
            elements.append(Spacer(1, 8))
            elements.append(create_metadata_table(item))
            elements.append(Spacer(1, 20))

            if (i+1) % 2 == 0:
                elements.append(PageBreak())
        else:
            elements.append(Paragraph(f"No spectral bands found for {item.id}", styles['Italic']))
            elements.append(Spacer(1, 8))

    doc.build(elements)
    print(f"Updated spectral report saved to {filename}")
    

if __name__ == "__main__":
    catalog_url = "https://wyvern-prod-public-open-data-program.s3.ca-central-1.amazonaws.com/catalog.json"
    catalog = Catalog.from_file(catalog_url)
    all_items = get_all_items(catalog)

    if not all_items:
        raise Exception("No items found in the catalog")

    create_spectral_pdf(all_items[:50])