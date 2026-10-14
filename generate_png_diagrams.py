"""
generate_png_diagrams.py
Generates professional ERD PNG diagrams using Pillow (pure Python).
No native C library dependency required.
"""

import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "--quiet"])

from PIL import Image, ImageDraw, ImageFont
import os

# ── Colours ──────────────────────────────────────────────────────────────────
BG          = "#1E1E2E"   # dark background
HEADER_BG   = "#313244"   # table header
ROW_BG      = "#262637"   # table row
BORDER      = "#89B4FA"   # blue border
PK_COL      = "#F9E2AF"   # gold for PK
FK_COL      = "#A6E3A1"   # green for FK
ATTR_COL    = "#CDD6F4"   # light text for attributes
TITLE_COL   = "#CBA6F7"   # purple title
LINE_COL    = "#89DCEB"   # relationship lines

W, H = 1400, 900
PAD  = 30
CELL = 24          # row height
TW   = 220         # table width
TH_H = 32          # header height

def make_canvas(w, h):
    img = Image.new("RGB", (w, h), BG)
    return img, ImageDraw.Draw(img)

def load_font(size, bold=False):
    try:
        path = "C:/Windows/Fonts/consola.ttf" if not bold else "C:/Windows/Fonts/consolab.ttf"
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def draw_table(draw, x, y, title, rows, title_font, row_font):
    """rows: list of (label, annotation) where annotation is 'PK','FK' or ''"""
    th = TH_H + len(rows) * CELL + 8
    # shadow
    draw.rectangle([x+4, y+4, x+TW+4, y+th+4], fill="#111122")
    # border
    draw.rectangle([x, y, x+TW, y+th], outline=BORDER, width=2)
    # header
    draw.rectangle([x, y, x+TW, y+TH_H], fill=HEADER_BG)
    draw.text((x + TW//2, y + TH_H//2), title, fill=TITLE_COL, font=title_font, anchor="mm")
    # rows
    for i, (label, ann) in enumerate(rows):
        ry = y + TH_H + i * CELL + 4
        row_fill = "#2A2A3E" if i % 2 == 0 else ROW_BG
        draw.rectangle([x+1, ry, x+TW-1, ry+CELL-2], fill=row_fill)
        colour = PK_COL if ann == "PK" else FK_COL if ann == "FK" else ATTR_COL
        prefix = "[PK] " if ann == "PK" else "[FK] " if ann == "FK" else "     "
        draw.text((x + 8, ry + CELL//2), prefix + label, fill=colour, font=row_font, anchor="lm")
    return x + TW//2, y + th   # centre-x, bottom-y

def arrow(draw, x1, y1, x2, y2, label=""):
    draw.line([(x1,y1),(x2,y2)], fill=LINE_COL, width=2)
    draw.ellipse([x2-5,y2-5,x2+5,y2+5], fill=LINE_COL)
    if label:
        mx, my = (x1+x2)//2, (y1+y2)//2
        font = load_font(11)
        draw.text((mx+4, my), label, fill=LINE_COL, font=font)

# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 1: 3NF Schema
# ══════════════════════════════════════════════════════════════════════════════
def make_3nf():
    img, draw = make_canvas(1100, 700)
    tf = load_font(13, bold=True)
    rf = load_font(11)

    # title
    draw.text((550, 22), "E-Commerce Source Database — 3NF Schema", fill=TITLE_COL,
              font=load_font(18, bold=True), anchor="mm")

    # users
    ux, uy = 80, 100
    _, ub = draw_table(draw, ux, uy, "users", [
        ("user_id INTEGER", "PK"),
        ("name VARCHAR(255)", ""),
        ("email VARCHAR(255)", ""),
        ("address VARCHAR(255)", ""),
        ("created_at TIMESTAMP", ""),
    ], tf, rf)

    # products
    px, py = 720, 100
    _, pb = draw_table(draw, px, py, "products", [
        ("product_id INTEGER", "PK"),
        ("name VARCHAR(255)", ""),
        ("category VARCHAR(255)", ""),
        ("price DECIMAL(10,2)", ""),
    ], tf, rf)

    # orders
    ox, oy = 80, 390
    ocx, _ = draw_table(draw, ox, oy, "orders", [
        ("order_id INTEGER", "PK"),
        ("user_id INTEGER", "FK"),
        ("order_date TIMESTAMP", ""),
    ], tf, rf)

    # order_items
    ix, iy = 400, 390
    icx, _ = draw_table(draw, ix, iy, "order_items", [
        ("order_item_id INTEGER", "PK"),
        ("order_id INTEGER", "FK"),
        ("product_id INTEGER", "FK"),
        ("quantity INTEGER", ""),
        ("total_price DECIMAL", ""),
    ], tf, rf)

    # relationships
    # users -> orders (1:many)
    arrow(draw, ux+TW//2, ub, ox+TW//2, oy, "1:N")
    # orders -> order_items (1:many)
    arrow(draw, ox+TW, oy+40, ix, iy+40, "1:N")
    # products -> order_items (1:many)
    arrow(draw, px+TW//2, py+180, ix+TW//2, iy, "1:N")

    # legend
    lx, ly = 820, 590
    draw.rectangle([lx, ly, lx+230, ly+80], outline=BORDER, width=1, fill=HEADER_BG)
    draw.text((lx+10, ly+10), "Legend:", fill=TITLE_COL, font=tf)
    draw.text((lx+10, ly+30), "[PK] Primary Key", fill=PK_COL, font=rf)
    draw.text((lx+10, ly+48), "[FK] Foreign Key", fill=FK_COL, font=rf)
    draw.text((lx+10, ly+66), "---- Relationship", fill=LINE_COL, font=rf)

    os.makedirs("diagrams", exist_ok=True)
    img.save("diagrams/3nf_schema.png", dpi=(150,150))
    print("  Saved: diagrams/3nf_schema.png")

# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 2: Star Schema
# ══════════════════════════════════════════════════════════════════════════════
def make_star():
    img, draw = make_canvas(1300, 900)
    tf = load_font(13, bold=True)
    rf = load_font(11)

    draw.text((650, 22), "Data Warehouse — Star Schema", fill=TITLE_COL,
              font=load_font(18, bold=True), anchor="mm")

    # ── fact_order_items (centre) ──
    fx, fy = 480, 340
    fcx, fcb = draw_table(draw, fx, fy, "fact_order_items", [
        ("order_item_id INTEGER", "PK"),
        ("user_sk INTEGER", "FK"),
        ("product_sk INTEGER", "FK"),
        ("date_sk INTEGER", "FK"),
        ("quantity INTEGER", ""),
        ("line_total DECIMAL", ""),
    ], tf, rf)

    # ── dim_user (left, SCD Type 2) ──
    ux, uy = 60, 280
    ucx, ucb = draw_table(draw, ux, uy, "dim_user  [SCD Type 2]", [
        ("user_sk INTEGER", "PK"),
        ("user_id INTEGER", ""),
        ("name VARCHAR(255)", ""),
        ("email VARCHAR(255)", ""),
        ("address VARCHAR(255)", ""),
        ("start_date TIMESTAMP", ""),
        ("end_date TIMESTAMP", ""),
        ("is_current BOOLEAN", ""),
    ], tf, rf)

    # ── dim_product (right) ──
    ppx, ppy = 900, 280
    draw_table(draw, ppx, ppy, "dim_product", [
        ("product_sk INTEGER", "PK"),
        ("product_id INTEGER", ""),
        ("product_name VARCHAR", ""),
        ("category VARCHAR(255)", ""),
        ("price DECIMAL(10,2)", ""),
    ], tf, rf)

    # ── dim_date (bottom) ──
    dx, dy = 480, 680
    draw_table(draw, dx, dy, "dim_date", [
        ("date_sk INTEGER", "PK"),
        ("full_date DATE", ""),
        ("year INTEGER", ""),
        ("month INTEGER", ""),
        ("month_name VARCHAR", ""),
        ("day INTEGER", ""),
    ], tf, rf)

    # relationship lines
    # dim_user -> fact
    arrow(draw, ux+TW, uy+100, fx, fy+50, "user_sk")
    # dim_product -> fact
    arrow(draw, ppx, ppy+100, fx+TW, fy+50, "product_sk")
    # dim_date -> fact
    arrow(draw, dx+TW//2, dy, fcx, fcb, "date_sk")

    # SCD note
    note_x, note_y = 60, 640
    draw.rectangle([note_x, note_y, note_x+280, note_y+110], fill="#1A2A1A", outline=FK_COL, width=1)
    draw.text((note_x+10, note_y+10), "SCD Type 2 Columns:", fill=FK_COL, font=tf)
    draw.text((note_x+10, note_y+32), "start_date: When version became active", fill=ATTR_COL, font=rf)
    draw.text((note_x+10, note_y+50), "end_date:   When version expired (NULL=active)", fill=ATTR_COL, font=rf)
    draw.text((note_x+10, note_y+68), "is_current: TRUE = active record", fill=ATTR_COL, font=rf)
    draw.text((note_x+10, note_y+88), "Each address change = new user_sk row", fill=PK_COL, font=rf)

    # legend
    lx, ly = 980, 640
    draw.rectangle([lx, ly, lx+240, ly+80], outline=BORDER, width=1, fill=HEADER_BG)
    draw.text((lx+10, ly+10), "Legend:", fill=TITLE_COL, font=tf)
    draw.text((lx+10, ly+30), "[PK] Surrogate Key (warehouse)", fill=PK_COL, font=rf)
    draw.text((lx+10, ly+48), "[FK] Foreign Key to dimension", fill=FK_COL, font=rf)
    draw.text((lx+10, ly+66), "---- Relationship (SK join)", fill=LINE_COL, font=rf)

    img.save("diagrams/star_schema.png", dpi=(150,150))
    print("  Saved: diagrams/star_schema.png")

make_3nf()
make_star()
print("Done!")
