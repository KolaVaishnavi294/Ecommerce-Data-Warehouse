import base64
import zlib
import urllib.request
import os

def generate_svg(mmd_file, svg_file):
    with open(mmd_file, 'r') as f:
        diagram = f.read()
    
    encoded = base64.urlsafe_b64encode(zlib.compress(diagram.encode('utf-8'), 9)).decode('ascii')
    url = f"https://kroki.io/mermaid/svg/{encoded}"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            svg = response.read().decode('utf-8')
            with open(svg_file, 'w') as out:
                out.write(svg)
        print(f"Generated {svg_file}")
    except Exception as e:
        print(f"Error generating {svg_file}: {e}")

generate_svg('diagrams/3nf_schema.mmd', 'diagrams/3nf_schema.svg')
generate_svg('diagrams/star_schema.mmd', 'diagrams/star_schema.svg')

# Cleanup the empty pngs
try:
    if os.path.exists('diagrams/3nf_schema.png'): os.remove('diagrams/3nf_schema.png')
    if os.path.exists('diagrams/star_schema.png'): os.remove('diagrams/star_schema.png')
except:
    pass
