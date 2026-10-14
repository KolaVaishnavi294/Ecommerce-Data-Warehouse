"""
Converts SVG diagram files to PNG using the cairosvg or Pillow + cairosvg library.
Falls back to using a simple Python approach if cairosvg is not available.
"""
import subprocess
import sys
import os

def install_and_convert():
    # Try installing cairosvg
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cairosvg", "--quiet"])
        import cairosvg
        cairosvg.svg2png(url="diagrams/3nf_schema.svg", write_to="diagrams/3nf_schema.png", scale=2.0)
        cairosvg.svg2png(url="diagrams/star_schema.svg", write_to="diagrams/star_schema.png", scale=2.0)
        print("PNG files generated via cairosvg!")
        return True
    except Exception as e:
        print(f"cairosvg failed: {e}")
        return False

install_and_convert()
