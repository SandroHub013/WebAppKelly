from PIL import Image, ImageDraw, ImageFont
import io
import math
import csv

def create_performance_heatmap(table_rows):
    """Crea una heatmap professionale delle performance di scommesse"""
    width = 900
    height = 600
    margin = 20
    img = Image.new("RGBA", (width, height), (25, 25, 25, 255))
    draw = ImageDraw.Draw(img)

    markets = []
    quotes = []
    data_matrix = {}
    win_rate_matrix = {}
    sample_matrix = {}
    
    current_market = None
    for row in table_rows:
        if row[0]:
            current_market = row[0]
            if current_market not in markets:
                markets.append(current_market)
        
        if current_market and row[1]:
            quota = row[1]
            if quota not in quotes:
                quotes.append(quota)
            
            try:
                roi = float(row[3].replace('%', '').replace('+', '').split('/')[0])
            except:
                roi = -100
            
            try:
                win_rate = float(row[2].replace('%', ''))
            except:
                win_rate = 0
            
            try:
                sample = int(row[5]) if len(row) > 5 and row[5] else 0
            except:
                sample = 0
            
            key = (current_market, quota)
            data_matrix[key] = roi
            win_rate_matrix[key] = win_rate
            sample_matrix[key] = sample

    left_margin = 160
    top_margin = 120
    cell_width = (width - left_margin - 120) // len(quotes)
    cell_height = (height - top_margin - 80) // len(markets)

    def get_font(size, bold=False):
        fonts_to_try = [
            "Arial", "Helvetica", "DejaVu Sans", "Liberation Sans",
            "Verdana", "Tahoma", "Calibri", "FreeSans"
        ]
        for font_name in fonts_to_try:
            try:
                return ImageFont.truetype(font_name, size)
            except:
                continue
        return ImageFont.load_default()

    title_font = get_font(20, True)
    header_font = get_font(12, True)
    cell_font = get_font(11)

    title = "HEATMAP PERFORMANCE SCOMMESSE - ANALISI ROI"
    draw.text((margin, margin), title, fill=(255, 255, 255, 255), font=title_font)

    subtitle = "Rosso = Perdita | Giallo = Neutro | Verde = Profitto"
    draw.text((margin, margin + 30), subtitle, fill=(180, 180, 180, 255), font=cell_font)

    for i, quota in enumerate(quotes):
        x = left_margin + i * cell_width + cell_width // 2
        y = top_margin - 15
        text_bbox = draw.textbbox((0, 0), quota, font=header_font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((x - text_width//2, y - 20), quota, fill=(220, 220, 220, 255), font=header_font)

    draw.text((left_margin + (len(quotes) * cell_width) // 2 - 50, top_margin - 45), 
              "FASCE DI QUOTA", fill=(200, 200, 200, 255), font=header_font)

    for i, market in enumerate(markets):
        y = top_margin + i * cell_height
        market_display = market[:20]
        draw.text((margin, y + cell_height//2 - 5), market_display, 
                  fill=(220, 220, 220, 255), font=header_font)

        for j, quota in enumerate(quotes):
            x = left_margin + j * cell_width
            key = (market, quota)
            roi = data_matrix.get(key)
            win_rate = win_rate_matrix.get(key)
            sample = sample_matrix.get(key, 0)

            if roi is not None:
                color = roi_to_gradient_color(roi)
                draw.rectangle(
                    [(x + 1, y + 1), (x + cell_width - 2, y + cell_height - 2)],
                    fill=color,
                    outline=(40, 40, 40, 255)
                )
                roi_text = f"{roi:+.0f}%"
                text_color = (255, 255, 255, 255) if roi < -30 or roi > 100 else (0, 0, 0, 255)
                roi_bbox = draw.textbbox((0, 0), roi_text, font=cell_font)
                roi_width = roi_bbox[2] - roi_bbox[0]
                draw.text((x + (cell_width - roi_width)//2, y + 8), 
                          roi_text, fill=text_color, font=cell_font)

                if win_rate > 0:
                    wr_text = f"{win_rate:.0f}%"
                    wr_color = (200, 200, 200, 255) if roi < -30 or roi > 100 else (80, 80, 80, 255)
                    wr_bbox = draw.textbbox((0, 0), wr_text, font=cell_font)
                    wr_width = wr_bbox[2] - wr_bbox[0]
                    draw.text((x + (cell_width - wr_width)//2, y + cell_height - 20), 
                              wr_text, fill=wr_color, font=cell_font)

                if sample > 0:
                    sample_color = (255, 100, 100, 255) if sample < 10 else (150, 150, 150, 255)
                    sample_text = str(sample)
                    draw.text((x + cell_width - 15, y + 2), sample_text, 
                              fill=sample_color, font=cell_font)
            else:
                draw.rectangle(
                    [(x + 1, y + 1), (x + cell_width - 2, y + cell_height - 2)],
                    fill=(35, 35, 35, 255),
                    outline=(40, 40, 40, 255)
                )

    scale_x = width - 90
    scale_y = top_margin
    scale_height = len(markets) * cell_height
    scale_width = 30

    for i in range(scale_height):
        roi_value = 200 - (i / scale_height) * 300
        color = roi_to_gradient_color(roi_value)
        draw.line([(scale_x, scale_y + i), (scale_x + scale_width, scale_y + i)], 
                  fill=color, width=1)

    draw.rectangle([(scale_x, scale_y), (scale_x + scale_width, scale_y + scale_height)],
                   outline=(100, 100, 100, 255), width=1)

    scale_labels = [
        (0, "+200%"),
        (scale_height // 4, "+100%"),
        (scale_height // 2, "0%"),
        (3 * scale_height // 4, "-50%"),
        (scale_height - 1, "-100%")
    ]
    for offset, label in scale_labels:
        draw.text((scale_x + scale_width + 5, scale_y + offset - 5), label, 
                  fill=(200, 200, 200, 255), font=cell_font)

    legend_y = height - 50
    legend_items = [
        ("■", (220, 50, 47, 255), "Evitare (ROI < -20%)"),
        ("■", (255, 193, 7, 255), "Marginale (-20% < ROI < +10%)"),
        ("■", (139, 195, 74, 255), "Discreto (+10% < ROI < +50%)"),
        ("■", (76, 175, 80, 255), "Buono (+50% < ROI < +100%)"),
        ("■", (0, 200, 83, 255), "Ottimo (ROI > +100%)")
    ]
    legend_x = margin
    for symbol, color, text in legend_items:
        draw.rectangle([(legend_x, legend_y), (legend_x + 12, legend_y + 12)], fill=color)
        draw.text((legend_x + 18, legend_y - 2), text, fill=(180, 180, 180, 255), font=cell_font)
        legend_x += 170

    info_text = "Numeri piccoli = campione | % grande = ROI | % piccola = Win Rate"
    draw.text((margin, height - 20), info_text, fill=(150, 150, 150, 255), font=cell_font)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

def roi_to_gradient_color(roi):
    breakpoints = [
        (-100, (220, 50, 47)),
        (-20, (244, 67, 54)),
        (0, (255, 193, 7)),
        (10, (255, 235, 59)),
        (50, (139, 195, 74)),
        (100, (76, 175, 80)),
        (200, (0, 200, 83))
    ]
    for i in range(len(breakpoints) - 1):
        roi1, color1 = breakpoints[i]
        roi2, color2 = breakpoints[i + 1]
        if roi1 <= roi <= roi2:
            t = (roi - roi1) / (roi2 - roi1)
            r = int(color1[0] + t * (color2[0] - color1[0]))
            g = int(color1[1] + t * (color2[1] - color1[1]))
            b = int(color1[2] + t * (color2[2] - color1[2]))
            return (r, g, b, 255)
    return (220, 50, 47, 255) if roi < -100 else (0, 200, 83, 255)

def load_data_from_csv(file_path):
    rows = []
    with open(file_path, encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Salta intestazione
        current_market = ""
        for row in reader:
            if not any(row):
                continue
            market = row[0].strip() if row[0].strip() else current_market
            current_market = market
            quota = row[1].strip()
            win_rate = row[2].strip()
            roi = row[3].strip()
            note = row[4].strip() if len(row) > 4 else ""
            campione = row[5].strip() if len(row) > 5 else ""
            rows.append([market, quota, win_rate, roi, note, campione])
    return rows

def generate_heatmap_from_csv(csv_path):
    data = load_data_from_csv(csv_path)
    return create_performance_heatmap(data)

if __name__ == "__main__":
    heatmap_buffer = generate_heatmap_from_csv("Export Bet-Analytix.csv")
    with open("performance_heatmap.png", "wb") as f:
        f.write(heatmap_buffer.getvalue())
