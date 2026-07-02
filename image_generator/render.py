from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import os
import requests
import re
import ast



ROOT_DIR = Path(__file__).resolve().parents[1]
BACKGROUND_DIR = ROOT_DIR / "background"
OUTPUT_DIR = ROOT_DIR / "output"
LOGO_CACHE_DIR = ROOT_DIR / "logos"
FONT_DIR = ROOT_DIR / "font"

COLORS = {
    "ink": "#2f3137",
    "dark": "#525564",
    "heading": "#161624",
    "soft_ink": "#454852",
    "label": "#a4a5b0",
    "muted": "#777b84",
    "faint": "#a4a8b0",
    "pink": "#ef5a78",
    "orange_deep": "#f56550",
    "orange": "#f28a35",
    "green": "#1f9d6a",
    "green_deep": "#269958",
    "red": "#d64a4a",
    "red_deep": "#d74434",
    "blue": "#3b82f6",
    "line": "#ececec",
    "white": "#ffffff",
    "off_white": "#f7f8fc",
    "footer": "#5a5c6c"
}


CATEGORY_COLORS = {
    "Dividend Announcement": COLORS["green"],
    "Stock Buyback": COLORS["green"],
    "IPO": COLORS["green"],
    "Rights Issue": COLORS["blue"],
    "Stock Split": COLORS["orange"],
    "Mergers & Acquisitions": COLORS["orange"],
    "Suspension": COLORS["red"],
    "Trading Halt": COLORS["red"],
    "Delisting": COLORS["red"],
    "Insider Trading": COLORS["pink"],
}

# Rarer / more impactful tags first — picked when a news has multiple Tier 1 tags.
CATEGORY_PRIORITY = [
    "Suspension",
    "Delisting",
    "Trading Halt",
    "Mergers & Acquisitions",
    "IPO",
    "Rights Issue",
    "Stock Buyback",
    "Stock Split",
    "Dividend Announcement",
    "Insider Trading",
]


def clean_company_name(name: str) -> str: 
    name = re.sub(r'\bPT\.?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r',?\s*Tbk\.?\s*$', '', name, flags=re.IGNORECASE)
    return name.strip()


def font(name="Inter-Bold.ttf", size=48):
    candidates = [
        FONT_DIR / name,
        Path("C:/Windows/Fonts/arialbd.ttf" if "Bold" in name else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def format_price(value: float) -> str:
    if value >= 1000:
        return f"{value:,.0f}".replace(",", ".")

    return str(int(value))


def format_date_range(window):
    """Human date range from a (start, end) pair of 'YYYY-MM-DD' strings.

    e.g. ('2026-06-12','2026-06-18') -> '12-18 Jun 2026'; collapses the shared
    month/year so the label stays short, expands them when they differ.
    """
    from datetime import datetime
    if not window or len(window) < 2:
        return ""
    try:
        s = datetime.strptime(str(window[0])[:10], "%Y-%m-%d")
        e = datetime.strptime(str(window[1])[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return ""
    if (s.year, s.month) == (e.year, e.month):
        return f"{s.day}-{e.day} {e.strftime('%b %Y')}"
    if s.year == e.year:
        return f"{s.day} {s.strftime('%b')} - {e.day} {e.strftime('%b %Y')}"
    return f"{s.strftime('%d %b %Y')} - {e.strftime('%d %b %Y')}"


def fit_font(draw, text, max_width, start_size, min_size=18, bold=True):
    filename = "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"
    size = start_size
    while size > min_size:
        fnt = font(filename, size)
        if draw.textbbox((0, 0), text, font=fnt)[2] <= max_width:
            return fnt
        size -= 2
    return font(filename, min_size)


def wrap_text(draw, text, fnt, max_width, max_lines=None):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    if max_lines and len(lines) > max_lines:
        kept = lines[:max_lines]
        kept[-1] = ellipsize_to_width(draw, kept[-1] + " " + " ".join(lines[max_lines:]), fnt, max_width)
        return kept
    return lines


def ellipsize_to_width(draw, text, fnt, max_width):
    text = str(text or "").strip()
    if draw.textbbox((0, 0), text, font=fnt)[2] <= max_width:
        return text
    suffix = "..."
    while text and draw.textbbox((0, 0), text + suffix, font=fnt)[2] > max_width:
        text = text[:-1].rstrip()
    return (text + suffix) if text else suffix


def draw_wrapped(draw, xy, text, fnt, fill, max_width, line_gap=8, max_lines=None):
    x, y = xy
    lines = wrap_text(draw, text, fnt, max_width, max_lines=max_lines)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def draw_wrapped_with_emphasis(draw, xy, text, fnt, fnt_emph, fill, fill_emph, max_width, line_gap=8, max_lines=None, pattern=r"\d"):
    import re
    rx = re.compile(pattern)
    space_w = draw.textlength(" ", font=fnt)
    words = str(text or "").split()

    meta = []
    for word in words:
        emph = bool(rx.search(word))
        f = fnt_emph if emph else fnt
        meta.append((word, emph, f, draw.textlength(word, font=f)))

    lines = []
    current = []
    current_w = 0
    for entry in meta:
        word_w = entry[3]
        if not current:
            current = [entry]
            current_w = word_w
        elif current_w + space_w + word_w <= max_width:
            current.append(entry)
            current_w += space_w + word_w
        else:
            lines.append(current)
            current = [entry]
            current_w = word_w
    if current:
        lines.append(current)

    if max_lines and len(lines) > max_lines:
        kept = lines[:max_lines]
        ellipsis = "…"
        ellipsis_w = draw.textlength(ellipsis, font=fnt)
        last = list(kept[-1])
        last_w = sum(w for _, _, _, w in last) + space_w * max(0, len(last) - 1)
        while last and last_w + ellipsis_w > max_width:
            removed = last.pop()
            last_w -= removed[3]
            if last:
                last_w -= space_w
        last.append((ellipsis, False, fnt, ellipsis_w))
        kept[-1] = last
        lines = kept

    x, y = xy
    for line in lines:
        cur_x = x
        for i, (word, emph, f, _) in enumerate(line):
            if i > 0:
                cur_x += space_w
            c = fill_emph if emph else fill
            draw.text((cur_x, y), word, font=f, fill=c)
            cur_x += draw.textlength(word, font=f)
        y += fnt.size + line_gap
    return y


def truncate_to_clause(draw, text, fnt, max_width, max_lines):
    import re
    text = str(text or "").strip()
    if not text:
        return text
    if len(wrap_text(draw, text, fnt, max_width, max_lines=None)) <= max_lines:
        return text
    boundaries = [m.end() for m in re.finditer(r"[.,;:]\s", text)]
    for end in sorted(boundaries, reverse=True):
        candidate = text[:end].rstrip(" ,;:.")
        if not candidate:
            continue
        candidate += "…"
        if len(wrap_text(draw, candidate, fnt, max_width, max_lines=None)) <= max_lines:
            return candidate
    return text


def relative_time(ts):
    from datetime import datetime, timezone
    if ts is None:
        return ""
    try:
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{int(seconds // 60)}m ago"
        if seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        return f"{int(seconds // 86400)}d ago"
    except Exception:
        return ""


def currency_idr(value):
    if value is None or str(value).lower() in {"nan", "none", ""}:
        return "-"
    try:
        value = float(value)
    except Exception:
        return "-"

    if abs(value) >= 1_000_000_000_000:
        val = value / 1_000_000_000_000
        return f"IDR {val:,.2f}T"
    if abs(value) >= 1_000_000_000:
        val = value / 1_000_000_000
        return f"IDR {val:,.2f}B"
    if abs(value) >= 1_000_000:
        val = value / 1_000_000
        return f"IDR {val:,.2f}M"
    return f"IDR {value:,.0f}"


def format_shares(value):
    """Format a raw share count as a compact suffixed string, e.g. 14_284_746 -> '14.28M'."""
    if value is None or str(value).lower() in {"nan", "none", ""}:
        return "-"
    try:
        value = float(value)
    except Exception:
        return "-"

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.2f}K"
    return f"{value:,.0f}"


def format_idr_short(value, signed=False):
    if value is None or str(value).lower() in {"nan", "none", ""}:
        return "-"
    try:
        value = float(value)
    except Exception:
        return "-"
    mag = abs(value)
    if mag >= 1_000_000_000_000:
        body = f"IDR {mag / 1_000_000_000_000:.1f}T"
    elif mag >= 1_000_000_000:
        body = f"IDR {mag / 1_000_000_000:.1f}B"
    elif mag >= 1_000_000:
        body = f"IDR {mag / 1_000_000:.1f}M"
    elif mag >= 1_000:
        body = f"IDR {mag / 1_000:.1f}K"
    else:
        body = f"IDR {mag:.0f}"
    if not signed:
        return body
    if value < 0:
        return f"−{body}"
    return f"+{body}"


COHORT_COLORS = {
    "Institutional": "blue",
    "Mixed": "orange",
    "Retail": "green",
}


def draw_progress_bar(draw, xy, width, height, fraction, fill, track="#ececec"):
    x, y = xy
    radius = height // 2
    draw.rounded_rectangle((x, y, x + width, y + height), radius=radius, fill=track)
    fill_w = int(width * max(0.0, min(1.0, fraction)))
    if fill_w >= radius * 2:
        draw.rounded_rectangle((x, y, x + fill_w, y + height), radius=radius, fill=fill)
    elif fill_w > 0:
        draw.rectangle((x, y, x + fill_w, y + height), fill=fill)


def pct(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "-"


def clean_text(value, fallback="-"):
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return fallback
    return text


def clean_slug(value):
    text = clean_text(value, "item").lower()
    return "".join(char if char.isalnum() else "_" for char in text).strip("_") or "item"


def normalize_tags(tags):
    if isinstance(tags, list):
        return [clean_text(tag) for tag in tags if clean_text(tag, "")]
    if not tags:
        return []
    return [clean_text(tags)]


def format_tickers(value):
    if isinstance(value, list):
        return " / ".join(clean_text(item, "") for item in value if clean_text(item, ""))
    text = clean_text(value, "")
    if not text:
        return ""
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return " / ".join(clean_text(item, "") for item in parsed if clean_text(item, ""))
        except Exception:
            pass
    return text


def source_label(value):
    text = clean_text(value, "")
    if not text:
        return "the linked source"
    host = urlparse(text).netloc
    if host:
        return host.replace("www.", "")
    return text[:48]


def clean_title(text):
    if not text:
        return ""
    # Remove leading/trailing whitespace
    text = str(text).strip()
    # Remove common symbols like - _ at the start or end
    import re
    text = re.sub(r'^[\s\-_/]+|[\s\-_/]+$', '', text)
    return text


from .renderers.insider_dark import InsiderEarningsRendererMixin


def clean_headline(text):
    if not text:
        return ""
    import re
    s = str(text)
    s = re.sub(r"\bPT\s+", "", s)
    s = re.sub(r"\s+Tbk\b\.?", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()


CATEGORY_SHORT = {
    "Mergers & Acquisitions": "M&A",
    "Dividend Announcement": "dividend",
    "Insider Trading": "insider",
    "Rights Issue": "rights",
    "Stock Buyback": "buyback",
    "Stock Split": "split",
    "Suspension": "suspension",
    "Trading Halt": "halt",
    "Delisting": "delisting",
    "IPO": "IPO",
}


class SocialImageRenderer(InsiderEarningsRendererMixin):
    CLUSTER_COLORS = {
        "buy": "#5BAA5A",
        "sell": "#D53E4F",
        "market": "#3288BD",
        "avg": "#6D5FA6",
    }
    CLUSTER_PALETTE = ["#3288BD", "#66C2A5", "#ABDDA4", "#FDAE61", "#F46D43", "#D53E4F", "#5E4FA2"]
    # Palette for dark-bg multi-stock charts — avoids greens & oranges reserved for buy/sell rings
    CROSS_DARK_PALETTE = ["#4FC3F7", "#CE93D8", "#FFD54F", "#F48FB1", "#80CBC4", "#B39DDB", "#4DD0E1"]

    # Colors for the dark IDX Fillings background variant
    IDX_CHAIN_COLORS = {
        "buy": "#A6D94E",
        "sell": "#F46D43",
        "market": "#3288BD",
        "avg": "#FDAE61",
    }
    # Shared card style for dark background: near-black neutral, 30% opacity
    IDX_DARK_CARD_FILL = (20, 20, 24, 77)
    IDX_DARK_BORDER = "#28282e"

    def __init__(self, background_dir=BACKGROUND_DIR, output_dir=OUTPUT_DIR):
        self.background_dir = Path(background_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        LOGO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.company_profiles = {}

    def _company(self, draw, image, xy, symbol, width, accent=COLORS["orange"]):
        x, y = xy
        card_h = 170
        self._card(draw, (x, y, x + width, y + card_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
        draw.rounded_rectangle((x, y, x + 10, y + card_h), radius=5, fill=accent)
        
        # Header Label
        draw.text((x + 34, y + 28), "COMPANY", font=font("Inter-Bold.ttf", 24), fill=COLORS["muted"])
        
        # Clean Ticker (no .JK)
        clean_symbol = str(symbol).upper().split(".")[0]
        
        # Align with other metric values which are drawn at y + 68
        content_y = y + 65
        
        # Logo inside card
        logo_size = 68  # Reduced by 25% (from 90)
        logo_y = content_y
        self._logo(image, (x + 34, logo_y), clean_symbol, size=logo_size, accent=accent)
        
        # Symbol & Name next to logo
        text_x = x + 34 + logo_size + 20
        draw.text((text_x, content_y - 2), clean_symbol, font=font("Inter-SemiBold.ttf", 36), fill=COLORS["ink"])
        
        # Full Company Name from profiles
        full_name = self.company_profiles.get(symbol) or self.company_profiles.get(clean_symbol) or "Public Company"
        
        # Implement wrapping for company name
        name_fnt = font("Inter-Regular.ttf", 22)
        name_x = text_x
        name_y = content_y + 42
        
        draw_wrapped(draw, (name_x, name_y), full_name, name_fnt, COLORS["soft_ink"], width - (name_x - x) - 20, line_gap=4, max_lines=2)

    def _logo(self, image, xy, symbol, size=100, accent=COLORS["pink"], extension="webp"):
        # Clean symbol (remove .JK if present)
        symbol = str(symbol).upper().split(".")[0]
        x, y = xy

        logo_img = None
        fallback_exts = [extension] if extension == "webp" else [extension, "webp"]
        
        for ext in fallback_exts:
            cache_path = LOGO_CACHE_DIR / f"{symbol}.{ext}"
            
            if cache_path.exists():
                try:
                    logo_img = Image.open(cache_path).convert("RGBA")
                    break
                
                except Exception:
                    pass

            if not logo_img:
                url = f"https://storage.googleapis.com/sectorsapp-sea/logo/{symbol}.{ext}"
                try:
                    resp = requests.get(url, timeout=4)
                    
                    if resp.status_code == 200:
                        logo_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                        
                        with open(cache_path, "wb") as f:
                            f.write(resp.content)
                        
                        break
                except Exception:
                    pass

        if logo_img:
            # Resize and mask to circle
            logo_img = ImageOps.fit(logo_img, (size, size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, size, size), fill=255)
            
            circular_logo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            circular_logo.paste(logo_img, (0, 0), mask)
            
            # Draw a subtle border/background for the logo
            draw = ImageDraw.Draw(image)
            draw.ellipse((x, y, x + size, y + size), fill="#ffffff", outline="#eeeeee", width=1)
            
            image.paste(circular_logo, (x, y), circular_logo)
        else:
            # Fallback to symbol initials if logo not found
            draw = ImageDraw.Draw(image)
            draw.ellipse((x, y, x + size, y + size), fill="#f8f8f8", outline="#eeeeee", width=1)
            symbol_char = symbol[:1].upper()
            fnt = font("Inter-Bold.ttf", int(size * 0.48))
            # Center the text
            bbox = draw.textbbox((0, 0), symbol_char, font=fnt)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((x + (size - tw) / 2, y + (size - th) / 2 - 5), symbol_char, font=fnt, fill=accent)

    def _open(self, template):
        return Image.open(self.background_dir / template).convert("RGBA")

    def _save(self, image, filename):
        path = self.output_dir / filename
        image.convert("RGB").save(path, quality=95)
        return path

    def _card(self, draw, xy, radius=28, fill="#ffffff", outline="#f0f0f0", width=3):
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

    def _line(self, draw, xy, fill=COLORS["line"], width=3):
        draw.line(xy, fill=fill, width=width)

    def _badge(self, draw, xy, text, fill=COLORS["pink"], font_size=28):
        x, y = xy
        fnt = font("Inter-Bold.ttf", font_size)
        bbox = draw.textbbox((0, 0), text, font=fnt)
        height = font_size + 22
        draw.rounded_rectangle((x, y, x + bbox[2] + 42, y + height), radius=height // 2, fill=fill)
        draw.text((x + 21, y + 10), text, font=fnt, fill=COLORS["white"])

    def _chip(self, draw, xy, text, fill="#fff5ed", text_fill=COLORS["orange"], font_size=24):
        x, y = xy
        fnt = font("Inter-Bold.ttf", font_size)
        bbox = draw.textbbox((0, 0), text, font=fnt)
        pad_x, pad_y = 22, 11
        height = font_size + pad_y * 2
        width = bbox[2] + pad_x * 2
        draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=fill)
        draw.text((x + pad_x, y + pad_y - 1), text, font=fnt, fill=text_fill)
        return x + width + 12


    def _metric(self, draw, xy, label, value, width, accent=COLORS["orange"]):
        x, y = xy
        metric_h = 170
        self._card(draw, (x, y, x + width, y + metric_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
        draw.rounded_rectangle((x, y, x + 10, y + metric_h), radius=5, fill=accent)
        draw.text((x + 34, y + 28), label.upper(), font=font("Inter-Bold.ttf", 24), fill=COLORS["muted"])
        
        # Scale font down if value is too long
        val_fnt = font("Inter-Bold.ttf", 38)
        if draw.textbbox((0, 0), value, font=val_fnt)[2] > width - 58:
            val_fnt = fit_font(draw, value, width - 58, 38, min_size=20, bold=True)
            
        # Don't wrap value, just draw single line with ellipsize if needed
        # Since it's a metric value, usually single line is better
        val_text = ellipsize_to_width(draw, value, val_fnt, width - 58)
        draw.text((x + 34, y + 68), val_text, font=val_fnt, fill=COLORS["ink"])

    def render_daily_filings(self, filings, date_label, filename="filings_daily.png"):
        image = self._open("News - Insider Trading.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        # Align the white cards with the template's INSIDER TRADING badge (its
        # left border sits at ~12.4% of width, not the usual 8%), so the badge,
        # the cards, and the date all share the same left/right edges.
        margin = int(w * 0.124)

        # Date this digest covers (the filing day): right edge flush with the
        # card edge, vertically centered on the template badge.
        if date_label:
            draw.text((w - margin, 240), str(date_label), font=font("Inter-Medium.ttf", 28),
                      fill=COLORS["muted"], anchor="rm")

        rows = list(filings)[:4]
        y = 360
        card_gap = 25
        card_h = 300  # Dipotong sedikit (dari 320)

        for i, row in enumerate(rows):
            txn_type = str(row.get("transaction_type", "")).strip().lower()
            if txn_type in {"buy", "sell"}:
                is_buy = txn_type == "buy"
            else:
                title_text = str(row.get("title", "")).lower()
                is_buy = "buy" in title_text or "purchase" in title_text
            accent_color = COLORS["green"] if is_buy else COLORS["red"]
            chip_bg = "#e6f4ea" if is_buy else "#fce8e8"
            
            # Card
            self._card(draw, (margin, y, w - margin, y + card_h), radius=24, fill="#ffffff", outline="#eeeeee", width=2)
            draw.rounded_rectangle((margin, y, margin + 10, y + card_h), radius=6, fill=accent_color)

            # Logo (96)
            logo_x, logo_y = margin + 35, y + 35
            symbol_raw = str(row.get("symbol", "?"))
            self._logo(image, (logo_x, logo_y), symbol_raw, size=96, accent=accent_color)

            # Content Area
            inner_x = logo_x + 130
            curr_y = y + 35
            
            # Symbol & Status Chip (Symbol SemiBold)
            symbol_text = symbol_raw
            symbol_fnt = font("Inter-SemiBold.ttf", 36)
            draw.text((inner_x, curr_y), symbol_text, font=symbol_fnt, fill=COLORS["ink"])
            
            status_text = "BUY" if is_buy else "SELL"
            chip_x = inner_x + draw.textlength(symbol_text, font=symbol_fnt) + 20
            chip_y = curr_y - 2
            chip_fnt = font("Inter-Bold.ttf", 24)
            arrow_size, pad, gap = 13, 16, 8
            text_w = draw.textlength(status_text, font=chip_fnt)
            chip_h = 24 + 20
            chip_w = pad + arrow_size + gap + text_w + pad
            draw.rounded_rectangle((chip_x, chip_y, chip_x + chip_w, chip_y + chip_h), radius=14, fill=chip_bg)
            self._trend_arrow(draw, (chip_x + pad, chip_y + (chip_h - arrow_size) // 2), up=is_buy, size=arrow_size, fill=accent_color, weight=3)
            draw.text((chip_x + pad + arrow_size + gap, chip_y + 8), status_text, font=chip_fnt, fill=accent_color)
            
            # Value (Top Right, SemiBold, format suffix + titik ribuan). Compute
            # widths first so the holder name can be fit to the space left of it.
            val_label = "Transaction Value"
            val_label_fnt = font("Inter-Regular.ttf", 22)
            val_fnt = font("Inter-SemiBold.ttf", 30)
            raw_val = row.get("transaction_value", 0)
            val_text = currency_idr(raw_val)
            val_block_left = (w - margin - 40) - max(
                draw.textlength(val_label, font=val_label_fnt),
                draw.textlength(val_text, font=val_fnt),
            )

            # Holder Name (SemiBold) — wrap to up to 2 lines (shrinking the font a
            # little if needed) so long institutional names (e.g. JPMorgan's full
            # legal name) show in full instead of being clipped, while staying
            # clear of the Transaction Value block on the right.
            curr_y += 55
            holder = row.get("holder_name") or "Individual/Institution"
            name_max_w = max(160, int(val_block_left - inner_x - 28))
            holder_size = 25
            holder_fnt = font("Inter-SemiBold.ttf", holder_size)
            name_lines = wrap_text(draw, holder, holder_fnt, name_max_w)
            while holder_size > 19 and len(name_lines) > 2:
                holder_size -= 1
                holder_fnt = font("Inter-SemiBold.ttf", holder_size)
                name_lines = wrap_text(draw, holder, holder_fnt, name_max_w)
            name_line_h = holder_size + 7
            name_lines = name_lines[:2]
            for li, line in enumerate(name_lines):
                draw.text((inner_x, curr_y + li * name_line_h), line, font=holder_fnt, fill=COLORS["soft_ink"])
            name_block_bottom = curr_y + len(name_lines) * name_line_h

            draw.text((w - margin - 40 - draw.textlength(val_label, font=val_label_fnt), y + 35), val_label, font=val_label_fnt, fill=COLORS["muted"])
            draw.text((w - margin - 40 - draw.textlength(val_text, font=val_fnt), y + 65), val_text, font=val_fnt, fill=COLORS["ink"])

            # Divider — sits below the name block, so it drops down on cards whose
            # name wrapped to 2 lines (single-line cards keep the original y+138).
            divider_y = max(y + 138, int(name_block_bottom + 14))
            draw.line((inner_x, divider_y, w - margin - 40, divider_y), fill="#acacac", width=1)
            
            # Metadata Row (Medium, font diperkecil 4: 28 -> 24)
            meta_y = divider_y + 22
            col_w = (w - margin * 2 - 170) // 4
            
            # Price fallback
            price_val = row.get("price")
            
            metas = [
                ("Shares", format_shares(row.get("amount_transaction"))),
                ("Price", currency_idr(price_val)),
                ("Before", f"{(row.get('share_percentage_before') or 0):.2f}%"),
                ("After", f"{(row.get('share_percentage_after') or 0):.2f}%")
            ]

            for j, (label, value) in enumerate(metas):
                col_x = inner_x + (j * col_w)
                draw.text((col_x, meta_y), label, font=font("Inter-Regular.ttf", 20), fill=COLORS["muted"])
                draw.text((col_x, meta_y + 35), value, font=font("Inter-Medium.ttf", 24), fill=COLORS["ink"])

                # Add tiny arrow for "After"
                if label == "After":
                    val_w = draw.textlength(value, font=font("Inter-Medium.ttf", 24))
                    self._trend_arrow(draw, (col_x + val_w + 12, meta_y + 42), up=is_buy, size=13, fill=accent_color, weight=3)

            y += card_h + card_gap

        return self._save(image, filename)


    def render_context_filing(self, group, filename=None):
        latest = group["latest"]
        image = self._open("News - Insider Trading.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        pattern = group.get("context_pattern", "Context")
        color = COLORS["green"] if "Buy" in pattern else COLORS["red"] if "Sell" in pattern else COLORS["pink"]
        
        # Header Badge
        self._badge(draw, (margin, 380), pattern.upper(), color, 30)
        
        # Title
        symbol = group.get('symbol', 'Ticker')
        title = f"{symbol} {pattern}"
        draw_wrapped(draw, (margin, 490), title, font("Inter-Bold.ttf", 88), COLORS["ink"], w - 2 * margin, 12, 2)
        
        # Add Logo next to title or in a fixed position
        self._logo(image, (w - margin - 120, 380), symbol, size=120, accent=color)
        
        # Context Card
        card_y = 680
        card_h = 320
        self._card(draw, (margin, card_y, w - margin, card_y + card_h), radius=32, fill="#ffffff", outline="#eeeeee", width=2)
        draw.rounded_rectangle((margin, card_y, margin + 12, card_y + card_h), radius=8, fill=color)
        
        inner_margin = margin + 50
        y = card_y + 50
        
        # Context inside the card
        context = latest.get("context") or latest.get("title") or "Context filing detected."
        draw_wrapped(draw, (inner_margin, y), context, font("Inter-Regular.ttf", 42), COLORS["soft_ink"], w - margin - inner_margin - 40, 10, 4)
        
        # Metrics Row
        y = card_y + card_h + 40
        metric_w = (w - margin * 2 - 40) // 2
        
        self._metric(draw, (margin, y), "Transactions", str(group.get("count", 1)), metric_w, color)
        self._metric(draw, (margin + metric_w + 40, y), "Latest Value", currency_idr(latest.get("transaction_value")), metric_w, COLORS["orange"])
        
        y += 190
        self._metric(draw, (margin, y), "Ownership", f"{pct(latest.get('share_percentage_before'))} -> {pct(latest.get('share_percentage_after'))}", metric_w, COLORS["pink"])
        holders = ", ".join(group.get("holders") or ["-"])
        self._metric(draw, (margin + metric_w + 40, y), "Holders", holders[:30] + ("..." if len(holders) > 30 else ""), metric_w, COLORS["muted"])

        # Price chart with buy/sell markers
        chart = self._cluster_chart(symbol, group.get("transactions", []))
        if chart:
            target_w = w - 2 * margin
            ratio = target_w / float(chart.width)
            chart = chart.resize((target_w, int(chart.height * ratio)), Image.Resampling.LANCZOS)
            chart_y = y + 200
            image.paste(chart, (margin, chart_y), chart)

        pattern_slug = pattern.lower().replace(" ", "_")
        return self._save(image, filename or f"filing_context_{group.get('symbol')}_{pattern_slug}.png")

    def render_tagged_filing(self, filing, filename=None):
        image = self._open("News - Insider Trading.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)
        
        tags = normalize_tags(filing.get("tags_parsed") or [])
        important = next((tag for tag in tags if tag.lower() in {"takeover", "mesop"}), tags[0] if tags else "Important Filing")
        
        accent_color = COLORS["orange"] if important.lower() == "takeover" else COLORS["pink"] if important.lower() == "mesop" else COLORS["green"]
        
        # Header Badge
        self._badge(draw, (margin, 380), str(important).upper(), accent_color, 30)

        # Title
        title = clean_title(filing.get("headline") or filing.get("title", "Important Filing"))
        title_fnt = fit_font(draw, title, w - 2 * margin, 72, 48, bold=True)
        y = draw_wrapped(draw, (margin, 490), title, title_fnt, COLORS["ink"], w - 2 * margin, 18, 4)
        
        y += 40
        # Horizontal Separator
        draw.line((margin, y, margin + 250, y), fill=accent_color, width=10)
        y += 60
        
        # Body / Summary Text
        summary = filing.get("body") or filing.get("summary") or filing.get("content") or ""
        if summary:
            summary_fnt = font("Inter-Regular.ttf", 38)
            y = draw_wrapped(draw, (margin, y), summary, summary_fnt, COLORS["soft_ink"], w - 2 * margin, 14, 5)
        
        y += 60
        
        # 2x2 Facts Grid
        metric_w = (w - margin * 2 - 40) // 2
        
        holder_name = filing.get("holder_name", "-")
        holder_short = holder_name[:25] + ("..." if len(holder_name) > 25 else "")
        
        change_text = f"{pct(filing.get('share_percentage_before'))} -> {pct(filing.get('share_percentage_after'))}"
        
        # Insider Chart Logic (Supabase integration)
        symbol_upper = str(filing.get("symbol", "")).upper()
        chart_path = None
        important_lower = str(important).lower()
        print(f"DEBUG: symbol={symbol_upper}, important={important_lower}, value={filing.get('transaction_value', 0)}")
        
        if "insider" in important_lower or filing.get("transaction_value", 0) > 0 or True: # Force true for testing
            try:
                import io
                import matplotlib.pyplot as plt
                import matplotlib.dates as mdates
                from datetime import datetime
                
                sb_url = os.getenv("SUPABASE_URL", "").rstrip("/")
                sb_key = os.getenv("SUPABASE_KEY", "")
                if not sb_url or not sb_key:
                    try:
                        from dotenv import load_dotenv
                        load_dotenv()
                        sb_url = os.getenv("SUPABASE_URL", "").rstrip("/")
                        sb_key = os.getenv("SUPABASE_KEY", "")
                    except ImportError:
                        pass
                
                print(f"DEBUG: sb_url={sb_url[:10] if sb_url else None}, sb_key={'[SET]' if sb_key else '[UNSET]'}")
                
                if sb_url and sb_key:
                    params = {
                        "select": "date,close",
                        "symbol": f"eq.{symbol_upper}",
                        "order": "date.desc",
                        "limit": "30"
                    }
                    headers = {
                        "apikey": sb_key,
                        "Authorization": f"Bearer {sb_key}"
                    }
                    r = requests.get(f"{sb_url}/rest/v1/idx_daily_data", params=params, headers=headers)
                    print(f"DEBUG: Supabase daily data status={r.status_code}")
                    if r.status_code == 200:
                        rows = r.json()
                        print(f"DEBUG: Retrieved {len(rows)} daily data rows")
                        if rows:
                            rows = sorted(rows, key=lambda x: x["date"])
                            dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in rows]
                            closes = [r["close"] for r in rows]

                            first_close = closes[-1]
                            last_close = closes[0]
                            is_green = first_close > last_close

                            GREEN = '#1B5E20'
                            RED = '#8B1538'
                            line_color = GREEN if is_green else RED

                            fig, ax = plt.subplots(figsize=(10, 4))
                            fig.patch.set_alpha(0.0)
                            ax.patch.set_alpha(0.0)
                            ax.plot(dates, closes, linewidth=2.5, color=line_color, zorder=3)

                            # Annotation point fallback
                            annot_date_str = filing.get("transaction_date") or str(filing.get("created_at", ""))[:10]
                            annot_close = None
                            annot_date = None
                            
                            print(f"DEBUG: annot_date_str={annot_date_str}")
                            try:
                                annot_date_dt = datetime.strptime(annot_date_str, "%Y-%m-%d")
                                annot_close = next((r["close"] for r in rows if r["date"] == annot_date_str), None)
                                if annot_close is None:
                                    earlier = [r for r in rows if r["date"] <= annot_date_str]
                                    if earlier:
                                        nearest = max(earlier, key=lambda r: r["date"])
                                        annot_close = nearest["close"]
                                        annot_date_dt = datetime.strptime(nearest["date"], "%Y-%m-%d")
                                annot_date = annot_date_dt
                                print(f"DEBUG: resolved annot_date={annot_date}, annot_close={annot_close}")
                            except Exception as e:
                                print(f"DEBUG: Annotation date parsing error: {e}")

                            if annot_date and annot_close:
                                ax.scatter([annot_date], [annot_close], s=120, color=RED, zorder=4, edgecolors='white', linewidths=2)
                                annot_text = f"{filing.get('holder_name', 'Insider')}\nIDR {filing.get('price', 0):,.0f}"
                                ax.annotate(
                                    annot_text,
                                    xy=(annot_date, annot_close),
                                    xytext=(-80, 30),
                                    textcoords='offset points',
                                    fontsize=10,
                                    fontweight='bold',
                                    color=RED,
                                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF5E1', edgecolor="#FD9D38", linewidth=1.5, alpha=0.9),
                                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', color=RED, linewidth=1.5),
                                    zorder=5
                                )

                            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                            plt.setp(ax.xaxis.get_majorticklabels(), ha='right')

                            for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
                            for spine in ['left', 'bottom']:
                                ax.spines[spine].set_color('#999')
                                ax.spines[spine].set_linewidth(1.5)
                            ax.tick_params(colors='#666', which='both', labelsize=10)
                            ax.grid(True, alpha=0.2, linestyle='--', color='#999')

                            buf = io.BytesIO()
                            plt.savefig(buf, format="png", dpi=120, bbox_inches="tight", transparent=True)
                            buf.seek(0)
                            chart_path = Image.open(buf).convert("RGBA")
                            plt.close(fig)
                            print("DEBUG: Chart generated successfully")
            except Exception as e:
                import traceback
                print(f"Chart error for {symbol_upper}: {e}")
                traceback.print_exc()

        self._company(draw, image, (margin, y - 20), filing.get("symbol", "-"), metric_w, accent_color)
        self._metric(draw, (margin + metric_w + 40, y - 20), "Holder", holder_short, metric_w, COLORS["muted"])
        
        y += 190 # Adjust spacing after first row of metrics (was y += 210 with unshifted y)
        
        self._metric(draw, (margin, y - 20), "Value", currency_idr(filing.get("transaction_value")), metric_w, COLORS["green"])
        self._metric(draw, (margin + metric_w + 40, y - 20), "Change", change_text, metric_w, COLORS["pink"])
        
        # If chart exists, adjust layout or paste chart at bottom
        if chart_path:
            chart_w, chart_h = chart_path.size
            
            # Scale chart to fit exactly the available width (align left with title)
            target_w = w - 2 * margin
            ratio = target_w / float(chart_w)
            chart_w = target_w
            chart_h = int(chart_h * ratio)
            chart_path = chart_path.resize((chart_w, chart_h), Image.Resampling.LANCZOS)
                
            # paste chart below metrics, starting slightly before margin to align inner plot
            c_x = margin - 15
            c_y = y + 200 # Place it just below the metrics
            print(f"DEBUG: Pacing chart at y={c_y}, image total height={h}")
            
            # draw card behind chart (removed to allow true transparency against main background)
            # self._card(draw, (margin, c_y, w - margin, c_y + chart_h + 20), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
            
            # composite using alpha channel as mask
            if chart_path.mode in ('RGBA', 'LA'):
                image.paste(chart_path, (c_x, c_y + 10), chart_path)
            else:
                image.paste(chart_path, (c_x, c_y + 10))


            
        symbol = clean_slug(filing.get("symbol", "filing"))
        return self._save(image, filename or f"filing_tag_{symbol}_{clean_slug(important)}.png")

    def _render_quick_stats(self, draw, xy, symbol, accent_color):
        x, y = xy
        w = 1080 - 2 * x
        h = 110
        self._card(draw, (x, y, x + w, y + h), radius=18, fill="#fdfdfd", outline="#eeeeee", width=2)
        
        # Placeholder stats
        stats = [
            ("SYMBOL", symbol),
            ("MKT CAP", "IDR 4.2T"),
            ("SECTOR", "Energy"),
            ("P/E", "12.4x")
        ]
        
        col_w = w // len(stats)
        for i, (label, val) in enumerate(stats):
            curr_x = x + (i * col_w) + 35
            draw.text((curr_x, y + 25), label, font=font("Inter-Bold.ttf", 20), fill=COLORS["muted"])
            draw.text((curr_x, y + 52), val, font=font("Inter-Bold.ttf", 30), fill=COLORS["ink"])

    def _pick_category(self, news):
        tags = news.get("tags_parsed") or []
        if not isinstance(tags, list):
            tags = []
        tag_set = set(tags)
        category = next((t for t in CATEGORY_PRIORITY if t in tag_set), None)
        if category is None:
            category = next((t for t in tags if t in CATEGORY_COLORS), "News")
        return category

    def render_tier1_digest(self, news_list, date_label, filename=None):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        EXCLUDED = {"Insider Trading", "Dividend Announcement", "IPO"}
        MAX_ROWS = 6
        MAX_PER_CATEGORY = 3
        logo_size = 64
        number_col_w = 44

        import re as _re
        from difflib import SequenceMatcher

        def _norm_headline(text):
            return _re.sub(r"[^a-z0-9]", "", clean_headline(text).lower())

        eligible = []
        seen_titles = set()
        seen_cat_ticker = set()
        norm_by_cat = {}
        for n in news_list:
            cat = self._pick_category(n)
            if cat in EXCLUDED:
                continue
            key = (n.get("title") or "").strip().lower()
            if not key or key in seen_titles:
                continue
            seen_titles.add(key)

            # Fuzzy near-duplicate guard: the same event often appears several times
            # worded slightly differently (and sometimes mis-tagged to a different
            # ticker). Record EVERY title-unique headline so later copies can be
            # matched against all earlier variants, not just the one we kept.
            norm = _norm_headline(n.get("title"))
            prev_norms = norm_by_cat.setdefault(cat, [])
            is_fuzzy_dup = bool(norm) and any(
                SequenceMatcher(None, norm, prev).ratio() >= 0.85 for prev in prev_norms
            )
            if norm:
                prev_norms.append(norm)
            if is_fuzzy_dup:
                continue

            tickers_str = format_tickers(n.get("tickers") or n.get("ticker") or n.get("symbol") or "")
            primary = next((t.strip().split(".")[0] for t in tickers_str.split("/") if t.strip()), "")
            cat_ticker_key = (cat, primary)
            if primary and cat_ticker_key in seen_cat_ticker:
                continue
            if primary:
                seen_cat_ticker.add(cat_ticker_key)
            eligible.append(n)

        buckets = {}
        for n in eligible:
            buckets.setdefault(self._pick_category(n), []).append(n)

        selected = []
        for cat in CATEGORY_PRIORITY:
            if cat in EXCLUDED or cat not in buckets:
                continue
            for item in buckets[cat][:MAX_PER_CATEGORY]:
                selected.append((cat, item))
                if len(selected) >= MAX_ROWS:
                    break
            if len(selected) >= MAX_ROWS:
                break

        y = 300
        prev_cat = None
        idx_global = 0

        for cat, news in selected:
            accent = CATEGORY_COLORS.get(cat, COLORS["orange"])

            if cat != prev_cat:
                header_fnt = font("Inter-Bold.ttf", 26)
                header_text = cat.upper()
                header_text_w = draw.textlength(header_text, font=header_fnt)
                header_h = 44
                draw.rounded_rectangle(
                    (margin, y, margin + header_text_w + 36, y + header_h),
                    radius=header_h // 2,
                    fill=accent,
                )
                draw.text((margin + 18, y + 8), header_text, font=header_fnt, fill=COLORS["white"])
                y += header_h + 24
                prev_cat = cat

            idx_global += 1

            tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
            tickers = [t.strip() for t in tickers_str.split("/") if t.strip()]
            extra_count = max(0, len(tickers) - 1)
            is_multi = extra_count > 0

            if tickers:
                logo_symbol = tickers[0]
            else:
                title_words = str(news.get("title") or "").replace("PT ", "").split()
                logo_symbol = title_words[0][:4].upper() if title_words else "?"

            num_fnt = font("Inter-Bold.ttf", 28)
            num_text = f"{idx_global:02d}"
            num_w = draw.textlength(num_text, font=num_fnt)
            draw.text((margin + (number_col_w - num_w) / 2 - 6, y + (logo_size - 28) / 2), num_text, font=num_fnt, fill=COLORS["faint"])

            logo_x = margin + number_col_w
            self._logo(image, (logo_x, y), logo_symbol, size=logo_size, accent=accent)

            if is_multi:
                badge_d = 32
                badge_x = logo_x + logo_size - badge_d + 6
                badge_y = y + logo_size - badge_d + 6
                draw.ellipse((badge_x, badge_y, badge_x + badge_d, badge_y + badge_d), fill=COLORS["ink"], outline=COLORS["white"], width=2)
                badge_fnt = font("Inter-Bold.ttf", 15)
                badge_text = f"+{extra_count}"
                tw = draw.textlength(badge_text, font=badge_fnt)
                draw.text((badge_x + (badge_d - tw) / 2, badge_y + 7), badge_text, font=badge_fnt, fill=COLORS["white"])

            right_x = logo_x + logo_size + 20

            cursor_x = right_x
            chip_h = 30
            if tickers:
                primary_ticker = tickers[0].split(".")[0]
                ticker_fnt = font("Inter-Bold.ttf", 22)
                ticker_text_w = draw.textlength(primary_ticker, font=ticker_fnt)
                ticker_pill_w = ticker_text_w + 22
                draw.rounded_rectangle(
                    (cursor_x, y + 2, cursor_x + ticker_pill_w, y + 2 + chip_h),
                    radius=chip_h // 2,
                    fill=COLORS["white"],
                    outline=accent,
                    width=2,
                )
                draw.text((cursor_x + 11, y + 6), primary_ticker, font=ticker_fnt, fill=COLORS["ink"])
                cursor_x += ticker_pill_w + 10

            headline_bottom = y + chip_h + 8
            headline = clean_headline(news.get("title"))
            if headline:
                headline_fnt = font("Inter-SemiBold.ttf", 26)
                headline_emph_fnt = font("Inter-Bold.ttf", 26)
                headline = truncate_to_clause(draw, headline, headline_fnt, w - right_x - margin, max_lines=3)
                headline_bottom = draw_wrapped_with_emphasis(
                    draw,
                    (right_x, y + chip_h + 12),
                    headline,
                    headline_fnt,
                    headline_emph_fnt,
                    COLORS["ink"],
                    accent,
                    w - right_x - margin,
                    line_gap=9,
                    max_lines=3,
                )

            if is_multi:
                strip_y = headline_bottom + 8
                strip_x = right_x
                strip_fnt = font("Inter-Bold.ttf", 14)
                visible = tickers[:4]
                hidden = len(tickers) - len(visible)
                for ticker in visible:
                    clean = ticker.split(".")[0]
                    tw = draw.textlength(clean, font=strip_fnt)
                    chip_w = tw + 18
                    chip_height = 24
                    draw.rounded_rectangle((strip_x, strip_y, strip_x + chip_w, strip_y + chip_height), radius=chip_height // 2, fill="#f0f0f0")
                    draw.text((strip_x + 9, strip_y + 4), clean, font=strip_fnt, fill=COLORS["muted"])
                    strip_x += chip_w + 6
                if hidden > 0:
                    more_text = f"+{hidden}"
                    draw.text((strip_x + 4, strip_y + 4), more_text, font=strip_fnt, fill=COLORS["muted"])
                headline_bottom = strip_y + 24

            y = headline_bottom + 48

        shown_ids = {id(item) for _, item in selected}
        more_count = sum(1 for n in eligible if id(n) not in shown_ids)
        if more_count > 0:
            pill_text = f"+ {more_count} more"
            pill_fnt = font("Inter-Regular.ttf", 22)
            pill_text_w = draw.textlength(pill_text, font=pill_fnt)
            pill_h = 36
            draw.rounded_rectangle(
                (margin, y + 8, margin + pill_text_w + 36, y + 8 + pill_h),
                radius=pill_h // 2,
                fill="#f0f0f0",
            )
            draw.text((margin + 18, y + 15), pill_text, font=pill_fnt, fill=COLORS["muted"])

            residual_cats = {}
            for n in eligible:
                if id(n) in shown_ids:
                    continue
                c = self._pick_category(n)
                residual_cats[c] = residual_cats.get(c, 0) + 1
            top = sorted(residual_cats.items(), key=lambda kv: -kv[1])[:3]
            top_keys = {k for k, _ in top}
            rest = sum(c for k, c in residual_cats.items() if k not in top_keys)
            parts = [f"{c} {CATEGORY_SHORT.get(k, k.lower())}" for k, c in top]
            if rest > 0:
                parts.append(f"{rest} other")
            note = " · ".join(parts) if parts else "from past 24h"
            note_fnt = font("Inter-Regular.ttf", 20)
            draw.text((margin + pill_text_w + 52, y + 16), note, font=note_fnt, fill=COLORS["faint"])
            y += pill_h + 16

        cta_fnt = font("Inter-SemiBold.ttf", 24)
        cta_text = "Visit sectors.app/indonesia/news to read more  →"
        draw.text((margin, y + 16), cta_text, font=cta_fnt, fill=COLORS["ink"])

        saved = self._save(image, filename or "news_tier1_digest.png")
        return str(saved)

    def render_tier2_news_summary(self, news_rows, date_label, filename="news_tier2_summary.png"):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        rows = list(news_rows)[:5]
        y = 260
        card_gap = 30
        card_h = 260
        
        # Color cycle for cards to match variety in expectation
        accent_colors = [COLORS["orange"], COLORS["green"], COLORS["pink"], COLORS["orange"], COLORS["red"]]

        for i, row in enumerate(rows):
            accent_color = accent_colors[i % len(accent_colors)]
            self._card(draw, (margin, y, w - margin, y + card_h), radius=24, fill="#ffffff", outline="#eeeeee", width=2)
            draw.rounded_rectangle((margin, y, margin + 10, y + card_h), radius=6, fill=accent_color)
            
            inner_x = margin + 40
            curr_y = y + 30
            
            # Tickers
            tickers_str = format_tickers(row.get("tickers") or row.get("ticker") or row.get("symbol") or "")
            tickers = [t.strip() for t in tickers_str.split("/") if t.strip()]
            
            curr_x = inner_x
            if tickers:
                for ticker in tickers[:2]:
                    curr_x = self._chip(draw, (curr_x, curr_y), ticker, fill=accent_color, text_fill=COLORS["white"], font_size=24)
                if len(tickers) > 2:
                    self._chip(draw, (curr_x, curr_y), f"+{len(tickers)-2}", fill="#f0f0f0", text_fill=COLORS["muted"], font_size=24)
            else:
                tags = normalize_tags(row.get("tags_parsed") or [])
                tag = tags[0] if tags else "News"
                self._chip(draw, (curr_x, curr_y), tag.upper(), fill=accent_color, text_fill=COLORS["white"], font_size=24)

            curr_y += 70
            
            # Title
            title = clean_title(row.get("title", "IDX News"))
            title_fnt = fit_font(draw, title, w - margin - inner_x - 30, 34, 28, bold=True)
            curr_y = draw_wrapped(draw, (inner_x, curr_y), title, title_fnt, COLORS["ink"], w - margin - inner_x - 30, 6, 2)
            
            # Small Summary (2 lines)
            summary = row.get("summary") or row.get("description") or row.get("body") or ""
            if summary:
                summary_fnt = font("Inter-Regular.ttf", 26)
                draw_wrapped(draw, (inner_x, curr_y + 4), summary, summary_fnt, COLORS["muted"], w - margin - inner_x - 30, 4, 2)

            y += card_h + card_gap

        if not rows:
            draw.text((margin, 600), "No notable news items today.", font=font("Inter-Bold.ttf", 54), fill=COLORS["muted"])

        return self._save(image, filename)

    def render_broker_bandar_scorecard(self, brokers, date_label, filename=None):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        y = 290

        header_fnt = font("Inter-Bold.ttf", 26)
        header_text = "BANDAR SCORECARD"
        header_text_w = draw.textlength(header_text, font=header_fnt)
        header_h = 44
        draw.rounded_rectangle(
            (margin, y, margin + header_text_w + 36, y + header_h),
            radius=header_h // 2,
            fill=COLORS["orange"],
        )
        draw.text((margin + 18, y + 8), header_text, font=header_fnt, fill=COLORS["white"])
        y += header_h + 14

        subtitle = f"{date_label} · top 10 brokers by gross turnover"
        draw.text((margin, y), subtitle, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 46

        rows = list(brokers)[:10]
        top5 = rows[:5]
        bottom5 = rows[5:10]

        number_col_w = 44
        swatch_size = 80
        card_h = 180

        for entry in top5:
            cohort_raw = entry.get("cohort")
            cohort = cohort_raw if isinstance(cohort_raw, str) and cohort_raw else "Mixed"
            cohort_color_key = COHORT_COLORS.get(cohort, "orange")
            accent = COLORS[cohort_color_key]

            rank = int(entry.get("rank") or 0)
            num_fnt = font("Inter-Bold.ttf", 28)
            num_text = f"{rank:02d}"
            num_w = draw.textlength(num_text, font=num_fnt)
            draw.text((margin + (number_col_w - num_w) / 2 - 6, y + (swatch_size - 28) / 2), num_text, font=num_fnt, fill=COLORS["faint"])

            swatch_x = margin + number_col_w
            draw.rounded_rectangle(
                (swatch_x, y, swatch_x + swatch_size, y + swatch_size),
                radius=16,
                fill=accent,
            )
            code = str(entry.get("broker_code") or "?")
            code_fnt = font("Inter-Bold.ttf", 36 if len(code) <= 2 else 28)
            code_w = draw.textlength(code, font=code_fnt)
            draw.text(
                (swatch_x + (swatch_size - code_w) / 2, y + (swatch_size - code_fnt.size) / 2 - 4),
                code,
                font=code_fnt,
                fill=COLORS["white"],
            )

            content_x = swatch_x + swatch_size + 18
            content_w = w - content_x - margin

            name_raw = entry.get("broker_name")
            name = name_raw if isinstance(name_raw, str) and name_raw else code
            name_fnt = font("Inter-SemiBold.ttf", 26)
            name_max = content_w - 240
            if draw.textlength(name, font=name_fnt) > name_max:
                while name and draw.textlength(name + "…", font=name_fnt) > name_max:
                    name = name[:-1]
                name = name.rstrip() + "…"
            draw.text((content_x, y + 2), name, font=name_fnt, fill=COLORS["ink"])

            badge_x = content_x + draw.textlength(name, font=name_fnt) + 12
            badge_fnt = font("Inter-Bold.ttf", 15)
            badge_h = 26
            badge_y = y + 6
            if entry.get("is_foreign"):
                bt = "FOREIGN"
                btw = draw.textlength(bt, font=badge_fnt)
                draw.rounded_rectangle(
                    (badge_x, badge_y, badge_x + btw + 14, badge_y + badge_h),
                    radius=badge_h // 2,
                    fill=COLORS["white"],
                    outline=COLORS["muted"],
                    width=1,
                )
                draw.text((badge_x + 7, badge_y + 4), bt, font=badge_fnt, fill=COLORS["muted"])
                badge_x += btw + 14 + 6
            cohort_text = cohort.upper()
            ctw = draw.textlength(cohort_text, font=badge_fnt)
            draw.rounded_rectangle(
                (badge_x, badge_y, badge_x + ctw + 14, badge_y + badge_h),
                radius=badge_h // 2,
                fill=accent,
            )
            draw.text((badge_x + 7, badge_y + 4), cohort_text, font=badge_fnt, fill=COLORS["white"])

            gross_text = format_idr_short(entry.get("gross_idr")) + " gross"
            gross_fnt = font("Inter-Bold.ttf", 30)
            draw.text((content_x, y + 42), gross_text, font=gross_fnt, fill=COLORS["ink"])
            gross_w = draw.textlength(gross_text, font=gross_fnt)

            net_val = entry.get("net_idr")
            net_text = format_idr_short(net_val, signed=True) + " net"
            net_fnt = font("Inter-SemiBold.ttf", 22)
            try:
                net_color = COLORS["green"] if float(net_val) >= 0 else COLORS["red"]
            except (TypeError, ValueError):
                net_color = COLORS["muted"]
            draw.text((content_x + gross_w + 16, y + 50), net_text, font=net_fnt, fill=net_color)

            line3_y = y + 112
            buy_sym = str(entry.get("top_buy_symbol") or "").split(".")[0]
            sell_sym = str(entry.get("top_sell_symbol") or "").split(".")[0]
            buy_amt = format_idr_short(entry.get("top_buy_net_idr"))
            sell_amt = format_idr_short(abs(entry.get("top_sell_net_idr") or 0))
            flow_fnt = font("Inter-SemiBold.ttf", 22)
            flow_emph_fnt = font("Inter-Bold.ttf", 22)

            buy_label = "▲ Buy "
            sell_label = "▼ Sell "
            label_fnt = font("Inter-SemiBold.ttf", 22)

            cur = content_x
            draw.text((cur, line3_y), buy_label, font=label_fnt, fill=COLORS["green"])
            cur += draw.textlength(buy_label, font=label_fnt)
            draw.text((cur, line3_y), buy_sym, font=flow_emph_fnt, fill=COLORS["ink"])
            cur += draw.textlength(buy_sym, font=flow_emph_fnt)
            draw.text((cur, line3_y), f" · {buy_amt}", font=flow_fnt, fill=COLORS["muted"])

            cur2 = content_x + (content_w // 2)
            draw.text((cur2, line3_y), sell_label, font=label_fnt, fill=COLORS["red"])
            cur2 += draw.textlength(sell_label, font=label_fnt)
            draw.text((cur2, line3_y), sell_sym, font=flow_emph_fnt, fill=COLORS["ink"])
            cur2 += draw.textlength(sell_sym, font=flow_emph_fnt)
            draw.text((cur2, line3_y), f" · {sell_amt}", font=flow_fnt, fill=COLORS["muted"])

            divider_y = y + card_h - 8
            draw.line((margin, divider_y, w - margin, divider_y), fill=COLORS["line"], width=1)

            y += card_h

        y += 10
        mini_h = 58
        mini_fnt = font("Inter-SemiBold.ttf", 22)
        mini_bold = font("Inter-Bold.ttf", 22)
        for entry in bottom5:
            rank = int(entry.get("rank") or 0)
            code = str(entry.get("broker_code") or "?")
            gross = format_idr_short(entry.get("gross_idr"))
            buy_sym = str(entry.get("top_buy_symbol") or "").split(".")[0]
            sell_sym = str(entry.get("top_sell_symbol") or "").split(".")[0]

            cur = margin
            rank_text = f"{rank:02d}"
            draw.text((cur, y + 12), rank_text, font=mini_bold, fill=COLORS["faint"])
            cur += draw.textlength(rank_text, font=mini_bold) + 16

            draw.text((cur, y + 12), code, font=mini_bold, fill=COLORS["ink"])
            cur += draw.textlength(code, font=mini_bold) + 14

            sep = "· "
            draw.text((cur, y + 12), sep, font=mini_fnt, fill=COLORS["faint"])
            cur += draw.textlength(sep, font=mini_fnt)

            draw.text((cur, y + 12), gross, font=mini_fnt, fill=COLORS["muted"])
            cur += draw.textlength(gross, font=mini_fnt) + 14

            draw.text((cur, y + 12), sep, font=mini_fnt, fill=COLORS["faint"])
            cur += draw.textlength(sep, font=mini_fnt)

            buy_chunk = f"Buy "
            draw.text((cur, y + 12), buy_chunk, font=mini_fnt, fill=COLORS["green"])
            cur += draw.textlength(buy_chunk, font=mini_fnt)
            draw.text((cur, y + 12), buy_sym, font=mini_bold, fill=COLORS["ink"])
            cur += draw.textlength(buy_sym, font=mini_bold) + 14

            draw.text((cur, y + 12), sep, font=mini_fnt, fill=COLORS["faint"])
            cur += draw.textlength(sep, font=mini_fnt)

            sell_chunk = f"Sell "
            draw.text((cur, y + 12), sell_chunk, font=mini_fnt, fill=COLORS["red"])
            cur += draw.textlength(sell_chunk, font=mini_fnt)
            draw.text((cur, y + 12), sell_sym, font=mini_bold, fill=COLORS["ink"])

            y += mini_h

        y += 16
        cta_fnt = font("Inter-SemiBold.ttf", 24)
        draw.text((margin, y), "See the full broker breakdown on sectors.app  →", font=cta_fnt, fill=COLORS["ink"])

        return self._save(image, filename or "broker_bandar_scorecard.png")

    def render_broker_bandar_scorecard_compact(self, brokers, date_label, filename=None):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        y = 290

        header_fnt = font("Inter-Bold.ttf", 26)
        header_text = "BANDAR SCORECARD"
        header_text_w = draw.textlength(header_text, font=header_fnt)
        header_h = 44
        draw.rounded_rectangle(
            (margin, y, margin + header_text_w + 36, y + header_h),
            radius=header_h // 2,
            fill=COLORS["orange"],
        )
        draw.text((margin + 18, y + 8), header_text, font=header_fnt, fill=COLORS["white"])
        y += header_h + 14

        subtitle = f"{date_label} · top 10 brokers by gross turnover"
        draw.text((margin, y), subtitle, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 46

        rows = list(brokers)[:10]
        number_col_w = 44
        swatch_size = 56
        row_h = 116

        for entry in rows:
            cohort_raw = entry.get("cohort")
            cohort = cohort_raw if isinstance(cohort_raw, str) and cohort_raw else "Mixed"
            cohort_color_key = COHORT_COLORS.get(cohort, "orange")
            accent = COLORS[cohort_color_key]

            rank = int(entry.get("rank") or 0)
            num_fnt = font("Inter-Bold.ttf", 26)
            num_text = f"{rank:02d}"
            num_w = draw.textlength(num_text, font=num_fnt)
            draw.text((margin + (number_col_w - num_w) / 2 - 6, y + (swatch_size - 26) / 2), num_text, font=num_fnt, fill=COLORS["faint"])

            swatch_x = margin + number_col_w
            draw.rounded_rectangle(
                (swatch_x, y, swatch_x + swatch_size, y + swatch_size),
                radius=12,
                fill=accent,
            )
            code = str(entry.get("broker_code") or "?")
            code_fnt = font("Inter-Bold.ttf", 26 if len(code) <= 2 else 20)
            code_w = draw.textlength(code, font=code_fnt)
            draw.text(
                (swatch_x + (swatch_size - code_w) / 2, y + (swatch_size - code_fnt.size) / 2 - 3),
                code,
                font=code_fnt,
                fill=COLORS["white"],
            )

            content_x = swatch_x + swatch_size + 16

            gross_text = format_idr_short(entry.get("gross_idr"))
            gross_fnt = font("Inter-Bold.ttf", 24)
            gross_w = draw.textlength(gross_text, font=gross_fnt)
            gross_x = w - margin - gross_w
            draw.text((gross_x, y + 4), gross_text, font=gross_fnt, fill=COLORS["ink"])

            name_raw = entry.get("broker_name")
            name = name_raw if isinstance(name_raw, str) and name_raw else code
            name_fnt = font("Inter-SemiBold.ttf", 24)
            name_max = gross_x - content_x - 16
            if draw.textlength(name, font=name_fnt) > name_max:
                while name and draw.textlength(name + "…", font=name_fnt) > name_max:
                    name = name[:-1]
                name = name.rstrip() + "…"
            draw.text((content_x, y + 6), name, font=name_fnt, fill=COLORS["ink"])

            buy_sym = str(entry.get("top_buy_symbol") or "").split(".")[0]
            sell_sym = str(entry.get("top_sell_symbol") or "").split(".")[0]
            buy_amt = format_idr_short(entry.get("top_buy_net_idr"))
            sell_amt = format_idr_short(abs(entry.get("top_sell_net_idr") or 0))
            flow_y = y + 46
            flow_fnt = font("Inter-SemiBold.ttf", 18)
            flow_bold = font("Inter-Bold.ttf", 18)

            cur = content_x
            buy_label = "▲ Buy "
            draw.text((cur, flow_y), buy_label, font=flow_fnt, fill=COLORS["green"])
            cur += draw.textlength(buy_label, font=flow_fnt)
            draw.text((cur, flow_y), buy_sym, font=flow_bold, fill=COLORS["ink"])
            cur += draw.textlength(buy_sym, font=flow_bold)
            buy_amt_text = f"  {buy_amt}"
            draw.text((cur, flow_y), buy_amt_text, font=flow_fnt, fill=COLORS["muted"])
            cur += draw.textlength(buy_amt_text, font=flow_fnt) + 16

            sep = "·  "
            draw.text((cur, flow_y), sep, font=flow_fnt, fill=COLORS["faint"])
            cur += draw.textlength(sep, font=flow_fnt)

            sell_label = "▼ Sell "
            draw.text((cur, flow_y), sell_label, font=flow_fnt, fill=COLORS["red"])
            cur += draw.textlength(sell_label, font=flow_fnt)
            draw.text((cur, flow_y), sell_sym, font=flow_bold, fill=COLORS["ink"])
            cur += draw.textlength(sell_sym, font=flow_bold)
            sell_amt_text = f"  {sell_amt}"
            draw.text((cur, flow_y), sell_amt_text, font=flow_fnt, fill=COLORS["muted"])

            cohort_short = cohort[0].upper() if cohort else "?"
            badge_fnt = font("Inter-Bold.ttf", 12)
            badge_x = gross_x + gross_w - 28
            badge_y = y + 38
            draw.rounded_rectangle(
                (badge_x, badge_y, badge_x + 28, badge_y + 18),
                radius=9,
                fill=accent,
            )
            bw = draw.textlength(cohort_short, font=badge_fnt)
            draw.text((badge_x + (28 - bw) / 2, badge_y + 3), cohort_short, font=badge_fnt, fill=COLORS["white"])
            if entry.get("is_foreign"):
                ftag = "F"
                fw = draw.textlength(ftag, font=badge_fnt)
                draw.rounded_rectangle(
                    (badge_x - 24, badge_y, badge_x - 4, badge_y + 18),
                    radius=9,
                    fill=COLORS["white"],
                    outline=COLORS["muted"],
                    width=1,
                )
                draw.text((badge_x - 24 + (20 - fw) / 2, badge_y + 3), ftag, font=badge_fnt, fill=COLORS["muted"])

            divider_y = y + row_h - 6
            draw.line((margin, divider_y, w - margin, divider_y), fill=COLORS["line"], width=1)

            y += row_h

        y += 16
        cta_fnt = font("Inter-SemiBold.ttf", 24)
        draw.text((margin, y), "See the full broker breakdown on sectors.app  →", font=cta_fnt, fill=COLORS["ink"])

        return self._save(image, filename or "broker_bandar_scorecard_compact.png")

    def render_broker_trending_movers(self, payload, date_label, filename=None):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        y = 290

        header_fnt = font("Inter-Bold.ttf", 26)
        header_text = "TRENDING MOVERS"
        htw = draw.textlength(header_text, font=header_fnt)
        hh = 44
        draw.rounded_rectangle(
            (margin, y, margin + htw + 36, y + hh),
            radius=hh // 2,
            fill=COLORS["pink"],
        )
        draw.text((margin + 18, y + 8), header_text, font=header_fnt, fill=COLORS["white"])
        y += hh + 14

        subtitle = f"{date_label} · top 5 stocks · who's buying, who's selling"
        draw.text((margin, y), subtitle, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 46

        stocks = list(payload.get("stocks", []))[:5]
        number_col_w = 44
        logo_size = 60
        card_h = 250

        for i, stock in enumerate(stocks):
            rank = i + 1

            num_fnt = font("Inter-Bold.ttf", 30)
            num_text = f"{rank:02d}"
            num_w = draw.textlength(num_text, font=num_fnt)
            draw.text(
                (margin + (number_col_w - num_w) / 2 - 6, y + (logo_size - 30) / 2),
                num_text, font=num_fnt, fill=COLORS["faint"],
            )

            logo_x = margin + number_col_w
            self._logo(image, (logo_x, y), stock["symbol"], size=logo_size, accent=COLORS["pink"])

            content_x = logo_x + logo_size + 16
            symbol = str(stock["symbol"]).split(".")[0]
            sym_fnt = font("Inter-Bold.ttf", 30)
            draw.text((content_x, y - 2), symbol, font=sym_fnt, fill=COLORS["ink"])
            sym_w = draw.textlength(symbol, font=sym_fnt)

            gross_text = format_idr_short(stock["gross_idr"])
            gross_fnt = font("Inter-Bold.ttf", 26)
            gross_w = draw.textlength(gross_text, font=gross_fnt)
            gross_x = w - margin - gross_w
            draw.text((gross_x, y + 2), gross_text, font=gross_fnt, fill=COLORS["ink"])

            company = stock.get("company") or ""
            company_fnt = font("Inter-Regular.ttf", 20)
            company_max = gross_x - (content_x + sym_w + 12) - 20
            if company and draw.textlength(company, font=company_fnt) > company_max:
                while company and draw.textlength(company + "…", font=company_fnt) > company_max:
                    company = company[:-1]
                company = company.rstrip() + "…"
            if company:
                draw.text((content_x + sym_w + 12, y + 4), f"· {company}", font=company_fnt, fill=COLORS["muted"])

            flow_y = y + 46
            flow_fnt = font("Inter-SemiBold.ttf", 20)
            f_net = stock.get("foreign_net", 0) or 0
            f_amt = format_idr_short(f_net, signed=True)
            f_color = COLORS["green"] if f_net >= 0 else COLORS["red"]
            direction_word = "net buy" if f_net >= 0 else "net sell"

            cur = content_x
            draw.text((cur, flow_y), "FOREIGN ", font=flow_fnt, fill=COLORS["muted"])
            cur += draw.textlength("FOREIGN ", font=flow_fnt)
            draw.text((cur, flow_y), f_amt, font=flow_fnt, fill=f_color)
            cur += draw.textlength(f_amt, font=flow_fnt) + 10
            draw.text((cur, flow_y), f"({direction_word})", font=flow_fnt, fill=COLORS["faint"])

            label_fnt = font("Inter-Bold.ttf", 18)
            chip_fnt = font("Inter-Bold.ttf", 17)
            chip_h = 32

            buy_y = y + 94
            draw.text((content_x, buy_y + 4), "▲ BUYERS", font=label_fnt, fill=COLORS["green"])
            cur = content_x + draw.textlength("▲ BUYERS  ", font=label_fnt) + 6
            for buyer in stock.get("buyers", [])[:3]:
                code = str(buyer.get("broker_code") or "?")
                amt = format_idr_short(buyer.get("net_idr", 0))
                chip_text = f"{code}  {amt}"
                ctw = draw.textlength(chip_text, font=chip_fnt)
                chip_w = ctw + 18
                draw.rounded_rectangle(
                    (cur, buy_y, cur + chip_w, buy_y + chip_h),
                    radius=chip_h // 2,
                    fill="#e8f5ee",
                    outline=COLORS["green"],
                    width=1,
                )
                draw.text((cur + 9, buy_y + 4), chip_text, font=chip_fnt, fill=COLORS["green"])
                cur += chip_w + 8

            sell_y = y + 144
            draw.text((content_x, sell_y + 4), "▼ SELLERS", font=label_fnt, fill=COLORS["red"])
            cur = content_x + draw.textlength("▼ SELLERS  ", font=label_fnt)
            for seller in stock.get("sellers", [])[:3]:
                code = str(seller.get("broker_code") or "?")
                amt = format_idr_short(abs(seller.get("net_idr", 0) or 0))
                chip_text = f"{code}  {amt}"
                ctw = draw.textlength(chip_text, font=chip_fnt)
                chip_w = ctw + 18
                draw.rounded_rectangle(
                    (cur, sell_y, cur + chip_w, sell_y + chip_h),
                    radius=chip_h // 2,
                    fill="#fdebea",
                    outline=COLORS["red"],
                    width=1,
                )
                draw.text((cur + 9, sell_y + 4), chip_text, font=chip_fnt, fill=COLORS["red"])
                cur += chip_w + 8

            volume = stock.get("volume_lots", 0) or 0
            trades = stock.get("trade_count", 0) or 0
            stats_text = f"{volume:,} lots · {trades:,} trades"
            stats_fnt = font("Inter-Regular.ttf", 16)
            draw.text((content_x, y + 196), stats_text, font=stats_fnt, fill=COLORS["faint"])

            divider_y = y + card_h - 12
            draw.line((margin, divider_y, w - margin, divider_y), fill=COLORS["line"], width=1)

            y += card_h

        y += 8
        cta_fnt = font("Inter-SemiBold.ttf", 24)
        draw.text((margin, y), "See full stock flow on sectors.app  →", font=cta_fnt, fill=COLORS["ink"])

        return self._save(image, filename or "broker_trending_movers.png")

    def render_broker_weekly_recap(self, brokers, date_label, filename=None):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        y = 290

        eyebrow_fnt = font("Inter-Bold.ttf", 22)
        draw.text((margin, y), "WEEKLY RECAP", font=eyebrow_fnt, fill=COLORS["orange_deep"])
        y += 36

        title_fnt = font("Inter-Bold.ttf", 56)
        y = draw_wrapped(draw, (margin, y), "Top 5 brokers this week", title_fnt, COLORS["ink"], w - 2 * margin, line_gap=4, max_lines=2)
        y += 8

        subtitle = f"{date_label} · ranked by gross turnover · vs prior week"
        draw.text((margin, y), subtitle, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 52

        rows = list(brokers)[:5]
        medal_colors = {1: "#D4A017", 2: "#A8A8A8", 3: "#B5651D"}

        card_h = 210
        swatch_size = 72
        number_col_w = 70

        for row in rows:
            rank = int(row["this_rank"])
            cohort_raw = row.get("cohort")
            cohort = cohort_raw if isinstance(cohort_raw, str) and cohort_raw else "Mixed"
            cohort_color_key = COHORT_COLORS.get(cohort, "orange")
            accent = COLORS[cohort_color_key]

            cx = margin + number_col_w // 2
            cy = y + swatch_size // 2
            if rank in medal_colors:
                r_outer = 30
                draw.ellipse(
                    (cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer),
                    fill=medal_colors[rank],
                )
                rank_fill = COLORS["white"]
            else:
                rank_fill = COLORS["faint"]
            rank_fnt = font("Inter-Bold.ttf", 36 if rank <= 3 else 30)
            rank_text = str(rank)
            rw = draw.textlength(rank_text, font=rank_fnt)
            draw.text(
                (cx - rw / 2, cy - rank_fnt.size / 2 - 4),
                rank_text, font=rank_fnt, fill=rank_fill,
            )

            swatch_x = margin + number_col_w + 16
            draw.rounded_rectangle(
                (swatch_x, y, swatch_x + swatch_size, y + swatch_size),
                radius=14, fill=accent,
            )
            code_raw = row.get("broker_code")
            code = code_raw if isinstance(code_raw, str) and code_raw else "?"
            code_fnt = font("Inter-Bold.ttf", 30 if len(code) <= 2 else 22)
            code_w = draw.textlength(code, font=code_fnt)
            draw.text(
                (swatch_x + (swatch_size - code_w) / 2, y + (swatch_size - code_fnt.size) / 2 - 4),
                code, font=code_fnt, fill=COLORS["white"],
            )

            content_x = swatch_x + swatch_size + 18

            name_raw = row.get("broker_name")
            name = name_raw if isinstance(name_raw, str) and name_raw else code
            name_fnt = font("Inter-SemiBold.ttf", 22)
            name_max = w - content_x - 240 - margin
            if draw.textlength(name, font=name_fnt) > name_max:
                while name and draw.textlength(name + "…", font=name_fnt) > name_max:
                    name = name[:-1]
                name = name.rstrip() + "…"
            draw.text((content_x, y + 2), name, font=name_fnt, fill=COLORS["ink"])

            cohort_text = cohort.upper()
            badge_fnt = font("Inter-Bold.ttf", 13)
            ctw = draw.textlength(cohort_text, font=badge_fnt)
            badge_x = content_x + draw.textlength(name, font=name_fnt) + 12
            badge_h = 22
            draw.rounded_rectangle(
                (badge_x, y + 6, badge_x + ctw + 14, y + 6 + badge_h),
                radius=badge_h // 2, fill=accent,
            )
            draw.text((badge_x + 7, y + 10), cohort_text, font=badge_fnt, fill=COLORS["white"])

            gross_text = format_idr_short(row.get("week_gross_idr")) + " gross"
            gross_fnt = font("Inter-Bold.ttf", 26)
            draw.text((content_x, y + 38), gross_text, font=gross_fnt, fill=COLORS["ink"])
            gw = draw.textlength(gross_text, font=gross_fnt)

            net_val = row.get("week_net_idr")
            net_text = format_idr_short(net_val, signed=True) + " net"
            net_fnt = font("Inter-SemiBold.ttf", 18)
            try:
                net_color = COLORS["green"] if float(net_val) >= 0 else COLORS["red"]
            except (TypeError, ValueError):
                net_color = COLORS["muted"]
            draw.text((content_x + gw + 16, y + 44), net_text, font=net_fnt, fill=net_color)

            prior_gross = row.get("prior_week_gross_idr")
            if prior_gross is not None and not (isinstance(prior_gross, float) and prior_gross != prior_gross):
                prior_text = f"prior week: {format_idr_short(prior_gross)}"
                prior_fnt = font("Inter-Regular.ttf", 16)
                draw.text((content_x, y + 80), prior_text, font=prior_fnt, fill=COLORS["faint"])

            label = row.get("rank_change_label", "—")
            if label.startswith("UP"):
                change_color = COLORS["green"]
                change_arrow = "▲"
            elif label.startswith("DOWN"):
                change_color = COLORS["red"]
                change_arrow = "▼"
            elif label == "NEW":
                change_color = COLORS["blue"]
                change_arrow = "★"
            else:
                change_color = COLORS["muted"]
                change_arrow = "="
            change_text = f"{change_arrow}  {label}"
            change_fnt = font("Inter-Bold.ttf", 20)
            ctw = draw.textlength(change_text, font=change_fnt)
            change_pad_h = 18
            change_pill_w = ctw + change_pad_h * 2
            change_pill_h = 44
            change_x = w - margin - change_pill_w
            change_y = y + (swatch_size - change_pill_h) // 2
            draw.rounded_rectangle(
                (change_x, change_y, change_x + change_pill_w, change_y + change_pill_h),
                radius=change_pill_h // 2,
                fill=change_color,
            )
            draw.text((change_x + change_pad_h, change_y + 11), change_text, font=change_fnt, fill=COLORS["white"])

            divider_y = y + card_h - 12
            draw.line((margin, divider_y, w - margin, divider_y), fill=COLORS["line"], width=1)

            y += card_h

        y += 8
        cta_fnt = font("Inter-SemiBold.ttf", 20)
        draw.text((margin, y), "See full weekly broker analysis on sectors.app  →", font=cta_fnt, fill=COLORS["ink"])

        return self._save(image, filename or "broker_weekly_recap.png")

    def render_weekly_accumulation(self, payload, display_range, filename=None):
        return self._render_weekly_flow(
            payload, display_range,
            header_text="MOST ACCUMULATED",
            header_color=COLORS["green"],
            direction="accumulated",
            chip_fill="#e8f5ee",
            chip_outline=COLORS["green"],
            chip_text=COLORS["green"],
            filename=filename or "weekly_accumulation.png",
        )

    def render_weekly_distribution(self, payload, display_range, filename=None):
        return self._render_weekly_flow(
            payload, display_range,
            header_text="MOST DISTRIBUTED",
            header_color=COLORS["red"],
            direction="distributed",
            chip_fill="#fdebea",
            chip_outline=COLORS["red"],
            chip_text=COLORS["red"],
            filename=filename or "weekly_distribution.png",
        )

    def _render_weekly_flow(self, payload, display_range, header_text, header_color, direction, chip_fill, chip_outline, chip_text, filename):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        y = 290

        header_fnt = font("Inter-Bold.ttf", 26)
        htw = draw.textlength(header_text, font=header_fnt)
        hh = 44
        draw.rounded_rectangle(
            (margin, y, margin + htw + 36, y + hh),
            radius=hh // 2, fill=header_color,
        )
        draw.text((margin + 18, y + 8), header_text, font=header_fnt, fill=COLORS["white"])
        y += hh + 14

        subtitle = f"{display_range} · top 5 stocks {direction} by foreign brokers"
        draw.text((margin, y), subtitle, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 46

        stocks = list(payload.get("stocks", []))[:5]
        number_col_w = 44
        logo_size = 56
        card_h = 220
        key = "buyers" if direction == "accumulated" else "sellers"
        arrow = "▲" if direction == "accumulated" else "▼"
        label_word = "BUYERS" if direction == "accumulated" else "SELLERS"

        for i, stock in enumerate(stocks):
            rank = i + 1

            num_fnt = font("Inter-Bold.ttf", 28)
            num_text = f"{rank:02d}"
            num_w = draw.textlength(num_text, font=num_fnt)
            draw.text(
                (margin + (number_col_w - num_w) / 2 - 6, y + (logo_size - 28) / 2),
                num_text, font=num_fnt, fill=COLORS["faint"],
            )

            logo_x = margin + number_col_w
            self._logo(image, (logo_x, y), stock["symbol"], size=logo_size, accent=header_color)

            content_x = logo_x + logo_size + 16
            symbol = str(stock["symbol"]).split(".")[0]
            sym_fnt = font("Inter-Bold.ttf", 26)
            draw.text((content_x, y - 2), symbol, font=sym_fnt, fill=COLORS["ink"])
            sym_w = draw.textlength(symbol, font=sym_fnt)

            headline_val = stock.get("foreign_net", 0) or 0
            net_text = format_idr_short(headline_val, signed=True)
            net_fnt = font("Inter-Bold.ttf", 24)
            net_w = draw.textlength(net_text, font=net_fnt)
            net_x = w - margin - net_w
            draw.text((net_x, y + 2), net_text, font=net_fnt, fill=header_color)

            company = stock.get("company") or ""
            company_fnt = font("Inter-Regular.ttf", 18)
            company_max = net_x - (content_x + sym_w + 12) - 20
            if company and draw.textlength(company, font=company_fnt) > company_max:
                while company and draw.textlength(company + "…", font=company_fnt) > company_max:
                    company = company[:-1]
                company = company.rstrip() + "…"
            if company:
                draw.text((content_x + sym_w + 12, y + 4), f"· {company}", font=company_fnt, fill=COLORS["muted"])

            gross_short = format_idr_short(stock.get("gross_idr", 0))
            trades = int(stock.get("trade_count", 0))
            stats_text = f"{gross_short} weekly gross  ·  {trades:,} trades"
            stats_fnt = font("Inter-Regular.ttf", 15)
            draw.text((content_x, y + 40), stats_text, font=stats_fnt, fill=COLORS["faint"])

            flow_y = y + 68
            flow_fnt = font("Inter-SemiBold.ttf", 18)
            f_net = stock.get("foreign_net", 0) or 0
            f_amt = format_idr_short(f_net, signed=True)
            f_color = COLORS["green"] if f_net >= 0 else COLORS["red"]
            direction_word = "net buy" if f_net >= 0 else "net sell"
            cur = content_x
            draw.text((cur, flow_y), "FOREIGN NET ", font=flow_fnt, fill=COLORS["muted"])
            cur += draw.textlength("FOREIGN NET ", font=flow_fnt)
            draw.text((cur, flow_y), f_amt, font=flow_fnt, fill=f_color)
            cur += draw.textlength(f_amt, font=flow_fnt) + 10
            draw.text((cur, flow_y), f"({direction_word})", font=flow_fnt, fill=COLORS["faint"])

            chip_y = y + 110
            chip_fnt = font("Inter-Bold.ttf", 15)
            chip_h = 28
            label_fnt = font("Inter-Bold.ttf", 16)
            label_text = f"{arrow} TOP FOREIGN {label_word}"
            draw.text((content_x, chip_y + 4), label_text, font=label_fnt, fill=chip_text)
            cur = content_x + draw.textlength(label_text + "    ", font=label_fnt)

            brokers = stock.get(key, [])[:3]
            for broker in brokers:
                code_raw = broker.get("broker_code")
                code = code_raw if isinstance(code_raw, str) and code_raw else "?"
                amt = format_idr_short(abs(broker.get("net_idr", 0) or 0))
                chip_text_str = f"{code}  {amt}"
                ctw = draw.textlength(chip_text_str, font=chip_fnt)
                chip_w = ctw + 18
                draw.rounded_rectangle(
                    (cur, chip_y, cur + chip_w, chip_y + chip_h),
                    radius=chip_h // 2, fill=chip_fill, outline=chip_outline, width=1,
                )
                draw.text((cur + 9, chip_y + 4), chip_text_str, font=chip_fnt, fill=chip_text)
                cur += chip_w + 8

            div_y = y + card_h - 12
            draw.line((margin, div_y, w - margin, div_y), fill=COLORS["line"], width=1)
            y += card_h

        y += 8
        cta_fnt = font("Inter-SemiBold.ttf", 24)
        draw.text((margin, y), "See full weekly flow on sectors.app  →", font=cta_fnt, fill=COLORS["ink"])

        return self._save(image, filename)

    def render_weekly_bandar_plays(self, payload, display_range, filename=None):
        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        y = 290

        header_text = "BANDAR OF THE WEEK"
        header_fnt = font("Inter-Bold.ttf", 26)
        htw = draw.textlength(header_text, font=header_fnt)
        hh = 44
        header_color = "#D4A017"  # gold-ish
        draw.rounded_rectangle(
            (margin, y, margin + htw + 36, y + hh),
            radius=hh // 2, fill=header_color,
        )
        draw.text((margin + 18, y + 8), header_text, font=header_fnt, fill=COLORS["white"])
        y += hh + 14

        subtitle = f"{display_range} · biggest single-stock conviction plays"
        draw.text((margin, y), subtitle, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 46

        plays = list(payload.get("plays", []))[:3]
        medal_colors = {1: "#D4A017", 2: "#A8A8A8", 3: "#B5651D"}
        card_h = 440

        for i, play in enumerate(plays):
            rank = i + 1

            # Rank medal circle on left
            rank_size = 56
            rank_x = margin
            rank_y = y
            draw.ellipse(
                (rank_x, rank_y, rank_x + rank_size, rank_y + rank_size),
                fill=medal_colors.get(rank, COLORS["muted"]),
            )
            rank_fnt = font("Inter-Bold.ttf", 32)
            rt = str(rank)
            rtw = draw.textlength(rt, font=rank_fnt)
            draw.text(
                (rank_x + (rank_size - rtw) / 2, rank_y + (rank_size - 32) / 2 - 4),
                rt, font=rank_fnt, fill=COLORS["white"],
            )

            # Broker swatch
            cohort_raw = play.get("cohort")
            cohort = cohort_raw if isinstance(cohort_raw, str) and cohort_raw else "Mixed"
            cohort_color_key = COHORT_COLORS.get(cohort, "orange")
            accent = COLORS[cohort_color_key]

            swatch_size = 72
            swatch_x = rank_x + rank_size + 16
            swatch_y = y
            draw.rounded_rectangle(
                (swatch_x, swatch_y, swatch_x + swatch_size, swatch_y + swatch_size),
                radius=14, fill=accent,
            )
            code_raw = play.get("broker_code")
            code = code_raw if isinstance(code_raw, str) and code_raw else "?"
            code_fnt = font("Inter-Bold.ttf", 28 if len(code) <= 2 else 22)
            code_w = draw.textlength(code, font=code_fnt)
            draw.text(
                (swatch_x + (swatch_size - code_w) / 2, swatch_y + (swatch_size - code_fnt.size) / 2 - 4),
                code, font=code_fnt, fill=COLORS["white"],
            )

            # Broker name + badges
            broker_x = swatch_x + swatch_size + 14
            broker_name_raw = play.get("broker_name")
            broker_name = broker_name_raw if isinstance(broker_name_raw, str) and broker_name_raw else code
            bn_fnt = font("Inter-SemiBold.ttf", 26)
            bn_max = (w - margin - 100 - broker_x)  # leave space for arrow and stock block
            actual_max = (w - margin) // 2 - broker_x - 20
            if draw.textlength(broker_name, font=bn_fnt) > actual_max:
                while broker_name and draw.textlength(broker_name + "…", font=bn_fnt) > actual_max:
                    broker_name = broker_name[:-1]
                broker_name = broker_name.rstrip() + "…"
            draw.text((broker_x, y + 2), broker_name, font=bn_fnt, fill=COLORS["ink"])

            # Cohort + foreign badges
            badge_y = y + 38
            badge_fnt = font("Inter-Bold.ttf", 14)
            badge_h = 24
            cur = broker_x
            cohort_text = cohort.upper()
            ctw = draw.textlength(cohort_text, font=badge_fnt)
            draw.rounded_rectangle(
                (cur, badge_y, cur + ctw + 14, badge_y + badge_h),
                radius=badge_h // 2, fill=accent,
            )
            draw.text((cur + 7, badge_y + 3), cohort_text, font=badge_fnt, fill=COLORS["white"])
            cur += ctw + 14 + 6
            if play.get("is_foreign"):
                ft = "FOREIGN"
                ftw = draw.textlength(ft, font=badge_fnt)
                draw.rounded_rectangle(
                    (cur, badge_y, cur + ftw + 14, badge_y + badge_h),
                    radius=badge_h // 2, fill=COLORS["white"], outline=COLORS["muted"], width=1,
                )
                draw.text((cur + 7, badge_y + 3), ft, font=badge_fnt, fill=COLORS["muted"])

            # Broker totals line
            bt_gross = format_idr_short(play.get("broker_total_gross", 0))
            bt_net = format_idr_short(play.get("broker_total_net", 0), signed=True)
            bt_text = f"{bt_gross} weekly gross · {bt_net} weekly net"
            bt_fnt = font("Inter-Regular.ttf", 16)
            draw.text((broker_x, y + 68), bt_text, font=bt_fnt, fill=COLORS["faint"])

            # Big arrow connector (between broker and stock blocks)
            arrow_fnt = font("Inter-Bold.ttf", 48)
            arrow_text = "→"
            arrow_w = draw.textlength(arrow_text, font=arrow_fnt)
            mid_x = w // 2
            # Stock block on right
            stock_x = mid_x + 40
            stock_logo_size = 64
            self._logo(image, (stock_x, y), str(play.get("symbol", "?")), size=stock_logo_size, accent=header_color)

            # Draw arrow centered between broker block and stock logo
            arrow_x = stock_x - 56
            draw.text((arrow_x, y + 6), arrow_text, font=arrow_fnt, fill=COLORS["muted"])

            stock_text_x = stock_x + stock_logo_size + 12
            sym = str(play.get("symbol", "?")).split(".")[0]
            sym_fnt = font("Inter-Bold.ttf", 28)
            draw.text((stock_text_x, y + 4), sym, font=sym_fnt, fill=COLORS["ink"])
            stock_company = play.get("company") or ""
            sc_fnt = font("Inter-Regular.ttf", 16)
            sc_max = w - margin - stock_text_x
            if stock_company and draw.textlength(stock_company, font=sc_fnt) > sc_max:
                while stock_company and draw.textlength(stock_company + "…", font=sc_fnt) > sc_max:
                    stock_company = stock_company[:-1]
                stock_company = stock_company.rstrip() + "…"
            if stock_company:
                draw.text((stock_text_x, y + 40), stock_company, font=sc_fnt, fill=COLORS["muted"])

            # Headline number
            net_text = f"{format_idr_short(play['net_idr'])} accumulated"
            net_fnt = font("Inter-Bold.ttf", 36)
            ntw = draw.textlength(net_text, font=net_fnt)
            draw.text(((w - ntw) / 2, y + 110), net_text, font=net_fnt, fill=header_color)

            # Two metric bars
            bar_x = margin + 40
            bar_w = w - margin * 2 - 80
            bar_h = 16

            # Concentration
            conc = float(play.get("concentration_pct", 0))
            label_fnt = font("Inter-SemiBold.ttf", 17)
            value_fnt = font("Inter-Bold.ttf", 18)
            conc_label = "CONCENTRATION"
            draw.text((bar_x, y + 188), conc_label, font=label_fnt, fill=COLORS["muted"])
            conc_value = f"{conc:.0f}%"
            cvw = draw.textlength(conc_value, font=value_fnt)
            draw.text((bar_x + bar_w - cvw, y + 188), conc_value, font=value_fnt, fill=header_color)
            draw_progress_bar(draw, (bar_x, y + 214), bar_w, bar_h, conc / 100.0, header_color)
            sub_label = f"of {code}'s total weekly buying"
            draw.text((bar_x, y + 236), sub_label, font=font("Inter-Regular.ttf", 14), fill=COLORS["faint"])

            # Stock share
            share = float(play.get("stock_share_pct", 0))
            share_label = "STOCK SHARE"
            draw.text((bar_x, y + 268), share_label, font=label_fnt, fill=COLORS["muted"])
            share_value = f"{share:.0f}%"
            svw = draw.textlength(share_value, font=value_fnt)
            draw.text((bar_x + bar_w - svw, y + 268), share_value, font=value_fnt, fill=header_color)
            draw_progress_bar(draw, (bar_x, y + 294), bar_w, bar_h, share / 100.0, header_color)
            sub_label2 = f"of all net buying into {sym} this week"
            draw.text((bar_x, y + 316), sub_label2, font=font("Inter-Regular.ttf", 14), fill=COLORS["faint"])

            # Narrative
            if conc >= 50:
                narrative = f"{code} accumulated {format_idr_short(play['net_idr'])} of {sym} — over half of their weekly buying went into this single stock."
            elif conc >= 25:
                narrative = f"{code} concentrated {conc:.0f}% of their weekly buying into {sym} — a clear conviction bet."
            else:
                narrative = f"{code} took a {format_idr_short(play['net_idr'])} position in {sym}, their largest single bet this week."
            nar_fnt = font("Inter-Regular.ttf", 17)
            draw_wrapped(draw, (margin, y + 360), narrative, nar_fnt, COLORS["ink"], w - margin * 2, line_gap=4, max_lines=2)

            # Divider
            div_y = y + card_h - 14
            draw.line((margin, div_y, w - margin, div_y), fill=COLORS["line"], width=1)

            y += card_h

        y += 8
        cta_fnt = font("Inter-SemiBold.ttf", 24)
        draw.text((margin, y), "See full broker plays on sectors.app  →", font=cta_fnt, fill=COLORS["ink"])

        return self._save(image, filename or "weekly_bandar_plays.png")
