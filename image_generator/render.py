import ast
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKGROUND_DIR = ROOT_DIR / "background"
OUTPUT_DIR = ROOT_DIR / "output"
LOGO_CACHE_DIR = ROOT_DIR / "logos"
FONT_DIR = ROOT_DIR / "font"

COLORS = {
    "ink": "#2f3137",
    "soft_ink": "#454852",
    "muted": "#777b84",
    "faint": "#a4a8b0",
    "pink": "#ef5a78",
    "orange": "#f28a35",
    "green": "#1f9d6a",
    "red": "#d64a4a",
    "line": "#ececec",
    "white": "#ffffff",
}


def font(name="Inter-Bold.ttf", size=48):
    candidates = [
        FONT_DIR / name,
        Path("C:/Windows/Fonts/arialbd.ttf" if "Bold" in name else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


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


class SocialImageRenderer:
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

    def _logo(self, image, xy, symbol, size=100, accent=COLORS["pink"]):
        # Clean symbol (remove .JK if present)
        symbol = str(symbol).upper().split(".")[0]
        x, y = xy
        logo_path = LOGO_CACHE_DIR / f"{symbol}.webp"
        
        logo_img = None
        if logo_path.exists():
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
            except Exception:
                pass

        if not logo_img:
            url = f"https://storage.googleapis.com/sectorsapp/logo/{symbol}.webp"
            try:
                resp = requests.get(url, timeout=4)
                if resp.status_code == 200:
                    logo_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                    with open(logo_path, "wb") as f:
                        f.write(resp.content)
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
        draw.rounded_rectangle((x, y, x + bbox[2] + 32, y + font_size + 20), radius=14, fill=fill)
        draw.text((x + 16, y + 8), text, font=fnt, fill=text_fill)
        return x + bbox[2] + 44

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
        margin = int(w * 0.08)

        rows = list(filings)[:4]
        y = 360
        card_gap = 25
        card_h = 300  # Dipotong sedikit (dari 320)

        for i, row in enumerate(rows):
            is_buy = "buy" in str(row.get("title", "")).lower() or "purchase" in str(row.get("title", "")).lower()
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
            
            status_text = "↗ BUY" if is_buy else "↘ SELL"
            chip_x = inner_x + draw.textlength(symbol_text, font=symbol_fnt) + 20
            self._chip(draw, (chip_x, curr_y - 2), status_text, fill=chip_bg, text_fill=accent_color, font_size=24)
            
            # Holder Name (SemiBold, diperkecil 3 -> 25)
            curr_y += 55
            holder = row.get("holder_name") or "Individual/Institution"
            draw.text((inner_x, curr_y), holder, font=font("Inter-SemiBold.ttf", 25), fill=COLORS["soft_ink"])
            
            # Title/Context (Regular, 22)
            curr_y += 35
            context = row.get("title_summarized") or clean_title(row.get("title", "Filing Transaction"))
            draw.text((inner_x, curr_y), context[:60] + ("..." if len(context) > 60 else ""), font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])

            # Value (Top Right, SemiBold, diperkecil 2: 32 -> 30, format suffix + titik ribuan)
            val_label = "Transaction Value"
            raw_val = row.get("transaction_value", 0)
            val_text = currency_idr(raw_val)
                
            draw.text((w - margin - 40 - draw.textlength(val_label, font=font("Inter-Regular.ttf", 22)), y + 35), val_label, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
            draw.text((w - margin - 40 - draw.textlength(val_text, font=font("Inter-SemiBold.ttf", 30)), y + 65), val_text, font=font("Inter-SemiBold.ttf", 30), fill=COLORS["ink"])

            # Divider (posisi disesuaikan dengan card_h baru)
            draw.line((inner_x, y + 165, w - margin - 40, y + 165), fill="#acacac", width=1)
            
            # Metadata Row (Medium, font diperkecil 4: 28 -> 24)
            meta_y = y + 185
            col_w = (w - margin * 2 - 170) // 4
            
            # Price fallback
            price_val = row.get("price")
            
            metas = [
                ("Shares (M)", f"{row.get('share_percentage_transaction', 0):.2f}"),
                ("Price", currency_idr(price_val)),
                ("Before", f"{row.get('share_percentage_before', 0):.2f}%"),
                ("After", f"{row.get('share_percentage_after', 0):.2f}%")
            ]
            
            for j, (label, value) in enumerate(metas):
                col_x = inner_x + (j * col_w)
                draw.text((col_x, meta_y), label, font=font("Inter-Regular.ttf", 20), fill=COLORS["muted"])
                draw.text((col_x, meta_y + 35), value, font=font("Inter-Medium.ttf", 24), fill=COLORS["ink"])
                
                # Add tiny arrow for "After"
                if label == "After":
                    arrow = "↗" if is_buy else "↘"
                    draw.text((col_x + draw.textlength(value, font=font("Inter-Medium.ttf", 24)) + 10, meta_y + 35), arrow, font=font("Inter-Medium.ttf", 24), fill=accent_color)

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

    def render_tier1_news_group(self, group, date_label, filename=None):
        category = group.get("category", "Tier 1 News")
        if category == "Dividend Announcement":
            return self.render_tier1_dividend_group(group, date_label, filename)
        if category == "Suspension":
            return self.render_tier1_suspension_group(group, date_label, filename)
        if category == "Rights Issue":
            return self.render_tier1_rights_issue_group(group, date_label, filename)
        if category == "IPO":
            return self.render_tier1_ipo_group(group, date_label, filename)
        if category == "Stock Buyback":
            return self.render_tier1_buyback_group(group, date_label, filename)

        news_list = group.get("news", [])
        
        template = "News - Insider Trading.png" if "Insider Trading" in category else "IDX - News 1.png"
        image = self._open(template)
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        accent_color = COLORS["pink"] if "Insider Trading" in category else COLORS["orange"]

        y = 310

        # Category Badge at the top
        self._badge(draw, (margin, y), category.upper(), fill=accent_color, font_size=30)
        
        y += 100

        # Group Title
        title = f"Notable {category} Updates"
        title_fnt = font("Inter-Bold.ttf", 64)
        y = draw_wrapped(draw, (margin, y), title, title_fnt, COLORS["ink"], w - 2 * margin, 18, 2)
        
        y += 30
        draw.line((margin, y, margin + 250, y), fill=accent_color, width=8)
        y += 50

        # Render each news item
        for i, news in enumerate(news_list[:3]):  # Max 3 items per group card
            # Tickers for this item
            tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
            tickers = [t.strip() for t in tickers_str.split("/") if t.strip()]
            
            if tickers:
                curr_x = margin
                
                # Color cycle for cards to match tier 2 variety
                accent_colors = [COLORS["orange"], COLORS["green"], COLORS["pink"], COLORS["red"]]
                ticker_accent = accent_colors[i % len(accent_colors)]
                
                for ticker in tickers[:2]:
                    curr_x = self._chip(draw, (curr_x, y), ticker, fill=ticker_accent, text_fill=COLORS["white"], font_size=22)
                y += 50
            
            # Item Headline
            headline = str(news.get("headline") or news.get("title", "News Update"))
            headline_fnt = font("Inter-SemiBold.ttf", 36)
            y = draw_wrapped(draw, (margin, y), headline, headline_fnt, COLORS["ink"], w - 2 * margin, 8, 2)
            y += 20
            
            # Bullets
            bullets = news.get("bullets")
            if bullets and isinstance(bullets, list):
                bullet_fnt = font("Inter-Regular.ttf", 28)
                for bullet in bullets[:2]:  # max 2 bullets per item in group view
                    clean_bullet = str(bullet).replace("**", "")
                    draw.text((margin, y), "•", font=font("Inter-Bold.ttf", 28), fill=accent_color)
                    y = draw_wrapped(draw, (margin + 30, y), clean_bullet, bullet_fnt, COLORS["soft_ink"], w - 2 * margin - 30, 8, 2)
                    y += 10
            
            y += 30

        slug = clean_slug(category)
        saved = self._save(image, filename or f"news_tier1_group_{slug}.png")
        return [(str(saved), news_list[:3])]

    def render_tier1_dividend_group(self, group, date_label, filename=None):
        category = group.get("category", "Dividend Announcement")
        news_list = group.get("news", [])
        
        accent_color = COLORS["green"] # Dividends are good!
        slug = clean_slug(category)
        
        cards_per_page = 3
        card_gap = 40
        card_h = 340
        
        pages = []
        for p_idx in range(0, len(news_list), cards_per_page):
            page_news = news_list[p_idx:p_idx + cards_per_page]

            image = self._open("IDX - News 1.png")
            draw = ImageDraw.Draw(image)
            w, h = image.size
            margin = int(w * 0.08)

            y = 330
            self._badge(draw, (margin, y), category.upper(), fill=accent_color, font_size=30)

            # Add Pagination indicator if multiple pages
            if len(news_list) > cards_per_page:
                page_num = (p_idx // cards_per_page) + 1
                total_pages = (len(news_list) + cards_per_page - 1) // cards_per_page
                page_text = f"Page {page_num} of {total_pages}"
                draw.text((w - margin - draw.textlength(page_text, font=font("Inter-Bold.ttf", 24)), y + 10), page_text, font=font("Inter-Bold.ttf", 24), fill=COLORS["muted"])

            y += 100

            title = "Dividend Announcements"
            title_fnt = font("Inter-Bold.ttf", 64)
            y = draw_wrapped(draw, (margin, y), title, title_fnt, COLORS["ink"], w - 2 * margin, 18, 2)
            y += 30
            draw.line((margin, y, margin + 250, y), fill=accent_color, width=8)
            y += 60

            for news in page_news:
                self._card(draw, (margin, y, w - margin, y + card_h), radius=24, fill="#ffffff", outline="#eeeeee", width=2)
                draw.rounded_rectangle((margin, y, margin + 10, y + card_h), radius=6, fill=accent_color)
                
                logo_x, logo_y = margin + 35, y + 35
                tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
                first_ticker = tickers_str.split("/")[0].strip() if tickers_str else "?"
                
                self._logo(image, (logo_x, logo_y), first_ticker, size=96, accent=accent_color)
                
                inner_x = logo_x + 130
                curr_y = y + 35
                
                # Headline
                headline = str(news.get("headline") or news.get("title", "Dividend News"))
                headline_fnt = font("Inter-SemiBold.ttf", 36)
                draw.text((inner_x, curr_y), first_ticker, font=font("Inter-Bold.ttf", 36), fill=COLORS["ink"])
                
                curr_y += 50
                draw_wrapped(draw, (inner_x, curr_y), headline, font("Inter-Regular.ttf", 26), COLORS["soft_ink"], w - margin - inner_x - 30, max_lines=2)
                
                # Dividend Data Grid
                grid_y = y + 150
                draw.line((inner_x, grid_y - 15, w - margin - 40, grid_y - 15), fill="#ececec", width=1)
                
                div_per_share = str(news.get("dividend_per_share") or "-")
                cum_date = str(news.get("cum_date") or "-")
                payout = str(news.get("payout_ratio") or "-")
                total_div = str(news.get("total_dividend") or "-")
                profit = str(news.get("profit_metric") or "-")
                
                metrics = [
                    ("Div/Share", div_per_share if div_per_share.startswith("IDR") else f"IDR {div_per_share}"),
                    ("Total Pool", total_div),
                    ("Cum Date", cum_date),
                    ("Net Profit", profit),
                    ("Payout", payout)
                ]
                
                col_w = (w - margin * 2 - 170) // 5
                for j, (label, val) in enumerate(metrics):
                    # Adjust font sizes for 5 columns so it doesn't look bizarre
                    # Give slightly more room or break text if needed, but primarily use a fixed smaller baseline font
                    col_x = inner_x + (j * col_w)
                    draw.text((col_x, grid_y), label, font=font("Inter-Regular.ttf", 18), fill=COLORS["muted"])
                    
                    # Force a consistent, smaller font for 5 columns instead of huge difference
                    val_fnt = font("Inter-Bold.ttf", 20)
                    
                    # Check length, scale font down strictly if needed
                    if draw.textbbox((0, 0), val, font=val_fnt)[2] > col_w - 5:
                        val_fnt = fit_font(draw, val, col_w - 5, 20, 14, bold=True)
                        
                    draw.text((col_x, grid_y + 35), val, font=val_fnt, fill=COLORS["ink"])
                
                # Historical Context Box inside card
                hist = news.get("dividend_history", [])
                if hist:
                    hist_y = grid_y + 90
                    draw.rounded_rectangle((inner_x, hist_y, w - margin - 40, hist_y + 70), radius=8, fill="#f8f9fa")
                    draw.text((inner_x + 15, hist_y + 22), "HISTORICAL:", font=font("Inter-Bold.ttf", 18), fill=COLORS["muted"])
                    
                    hist_x = inner_x + 150
                    for h_item in hist[:3]: # last 3 payments
                        h_date = str(h_item.get("date", ""))[:4] # Just year
                        h_val = h_item.get("dividend", 0)
                        draw.text((hist_x, hist_y + 20), f"IDR {h_val} ({h_date})", font=font("Inter-Medium.ttf", 20), fill=COLORS["soft_ink"])
                        hist_x += 200

                y += card_h + card_gap
                
            page_filename = filename or f"news_tier1_group_{slug}.png"
            if len(news_list) > cards_per_page:
                base, ext = os.path.splitext(page_filename)
                page_filename = f"{base}_p{(p_idx // cards_per_page) + 1}{ext}"
                
            saved_path = self._save(image, page_filename)
            pages.append((str(saved_path), page_news))

        return pages

    def render_tier1_suspension_group(self, group, date_label, filename=None):
        category = group.get("category", "Suspension")
        news_list = group.get("news", [])

        accent_color = COLORS["red"]
        slug = clean_slug(category)

        cards_per_page = 3
        card_gap = 40
        card_h = 340

        pages = []
        for p_idx in range(0, len(news_list), cards_per_page):
            page_news = news_list[p_idx:p_idx + cards_per_page]

            image = self._open("IDX - News 1.png")
            draw = ImageDraw.Draw(image)
            w, h = image.size
            margin = int(w * 0.08)

            y = 330
            self._badge(draw, (margin, y), category.upper(), fill=accent_color, font_size=30)

            if len(news_list) > cards_per_page:
                page_num = (p_idx // cards_per_page) + 1
                total_pages = (len(news_list) + cards_per_page - 1) // cards_per_page
                page_text = f"Page {page_num} of {total_pages}"
                draw.text((w - margin - draw.textlength(page_text, font=font("Inter-Bold.ttf", 24)), y + 10), page_text, font=font("Inter-Bold.ttf", 24), fill=COLORS["muted"])

            y += 100

            title = "Trading Suspensions"
            title_fnt = font("Inter-Bold.ttf", 64)
            y = draw_wrapped(draw, (margin, y), title, title_fnt, COLORS["ink"], w - 2 * margin, 18, 2)
            y += 30
            draw.line((margin, y, margin + 250, y), fill=accent_color, width=8)
            y += 60

            for news in page_news:
                self._card(draw, (margin, y, w - margin, y + card_h), radius=24, fill="#ffffff", outline="#eeeeee", width=2)
                draw.rounded_rectangle((margin, y, margin + 10, y + card_h), radius=6, fill=accent_color)

                logo_x, logo_y = margin + 35, y + 35
                tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
                first_ticker = tickers_str.split("/")[0].strip() if tickers_str else "?"

                self._logo(image, (logo_x, logo_y), first_ticker, size=96, accent=accent_color)

                inner_x = logo_x + 130
                curr_y = y + 35

                headline = str(news.get("headline") or news.get("title", "Trading Suspended"))
                draw.text((inner_x, curr_y), first_ticker, font=font("Inter-Bold.ttf", 36), fill=COLORS["ink"])

                curr_y += 50
                draw_wrapped(draw, (inner_x, curr_y), headline, font("Inter-Regular.ttf", 26), COLORS["soft_ink"], w - margin - inner_x - 30, max_lines=2)

                grid_y = y + 150
                draw.line((inner_x, grid_y - 15, w - margin - 40, grid_y - 15), fill="#ececec", width=1)

                reason = str(news.get("reason") or "-")
                effective = str(news.get("effective_date") or "-")
                last_price = str(news.get("last_price") or "-")
                resumes = str(news.get("expected_resumption") or "-")

                metrics = [
                    ("Reason", reason),
                    ("Effective", effective),
                    ("Last Price", last_price),
                    ("Resumes", resumes),
                ]

                col_w = (w - margin * 2 - 170) // 4
                for j, (label, val) in enumerate(metrics):
                    col_x = inner_x + (j * col_w)
                    draw.text((col_x, grid_y), label, font=font("Inter-Regular.ttf", 18), fill=COLORS["muted"])

                    val_fnt = font("Inter-Bold.ttf", 20)
                    if draw.textbbox((0, 0), val, font=val_fnt)[2] > col_w - 5:
                        val_fnt = fit_font(draw, val, col_w - 5, 20, 14, bold=True)

                    draw.text((col_x, grid_y + 35), val, font=val_fnt, fill=COLORS["ink"])

                y += card_h + card_gap

            page_filename = filename or f"news_tier1_group_{slug}.png"
            if len(news_list) > cards_per_page:
                base, ext = os.path.splitext(page_filename)
                page_filename = f"{base}_p{(p_idx // cards_per_page) + 1}{ext}"

            saved_path = self._save(image, page_filename)
            pages.append((str(saved_path), page_news))

        return pages

    def _render_tier1_metric_group(self, group, date_label, accent_color, title, metric_keys, filename=None):
        category = group.get("category", title)
        news_list = group.get("news", [])
        slug = clean_slug(category)

        cards_per_page = 3
        card_gap = 40
        card_h = 340

        pages = []
        for p_idx in range(0, len(news_list), cards_per_page):
            page_news = news_list[p_idx:p_idx + cards_per_page]

            image = self._open("IDX - News 1.png")
            draw = ImageDraw.Draw(image)
            w, h = image.size
            margin = int(w * 0.08)

            y = 330
            self._badge(draw, (margin, y), category.upper(), fill=accent_color, font_size=30)

            if len(news_list) > cards_per_page:
                page_num = (p_idx // cards_per_page) + 1
                total_pages = (len(news_list) + cards_per_page - 1) // cards_per_page
                page_text = f"Page {page_num} of {total_pages}"
                draw.text((w - margin - draw.textlength(page_text, font=font("Inter-Bold.ttf", 24)), y + 10), page_text, font=font("Inter-Bold.ttf", 24), fill=COLORS["muted"])

            y += 100

            title_fnt = font("Inter-Bold.ttf", 64)
            y = draw_wrapped(draw, (margin, y), title, title_fnt, COLORS["ink"], w - 2 * margin, 18, 2)
            y += 30
            draw.line((margin, y, margin + 250, y), fill=accent_color, width=8)
            y += 60

            for news in page_news:
                self._card(draw, (margin, y, w - margin, y + card_h), radius=24, fill="#ffffff", outline="#eeeeee", width=2)
                draw.rounded_rectangle((margin, y, margin + 10, y + card_h), radius=6, fill=accent_color)

                logo_x, logo_y = margin + 35, y + 35
                tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
                first_ticker = tickers_str.split("/")[0].strip() if tickers_str else "?"

                self._logo(image, (logo_x, logo_y), first_ticker, size=96, accent=accent_color)

                inner_x = logo_x + 130
                curr_y = y + 35

                headline = str(news.get("headline") or news.get("title", "Update"))
                draw.text((inner_x, curr_y), first_ticker, font=font("Inter-Bold.ttf", 36), fill=COLORS["ink"])
                curr_y += 50
                draw_wrapped(draw, (inner_x, curr_y), headline, font("Inter-Regular.ttf", 26), COLORS["soft_ink"], w - margin - inner_x - 30, max_lines=2)

                grid_y = y + 150
                draw.line((inner_x, grid_y - 15, w - margin - 40, grid_y - 15), fill="#ececec", width=1)

                metrics = [(label, str(news.get(key) or "-")) for label, key in metric_keys]
                ncols = len(metrics)
                col_w = (w - margin * 2 - 170) // ncols
                for j, (label, val) in enumerate(metrics):
                    col_x = inner_x + (j * col_w)
                    draw.text((col_x, grid_y), label, font=font("Inter-Regular.ttf", 18), fill=COLORS["muted"])
                    val_fnt = font("Inter-Bold.ttf", 20)
                    if draw.textbbox((0, 0), val, font=val_fnt)[2] > col_w - 5:
                        val_fnt = fit_font(draw, val, col_w - 5, 20, 14, bold=True)
                    draw.text((col_x, grid_y + 35), val, font=val_fnt, fill=COLORS["ink"])

                y += card_h + card_gap

            page_filename = filename or f"news_tier1_group_{slug}.png"
            if len(news_list) > cards_per_page:
                base, ext = os.path.splitext(page_filename)
                page_filename = f"{base}_p{(p_idx // cards_per_page) + 1}{ext}"

            saved_path = self._save(image, page_filename)
            pages.append((str(saved_path), page_news))

        return pages

    def render_tier1_rights_issue_group(self, group, date_label, filename=None):
        return self._render_tier1_metric_group(
            group, date_label,
            accent_color=COLORS["orange"],
            title="Rights Issues",
            metric_keys=[
                ("Issue Price", "issue_price"),
                ("Ratio", "ratio"),
                ("Size", "total_size"),
                ("Cum Date", "cum_date"),
                ("Use of Funds", "use_of_funds"),
            ],
            filename=filename,
        )

    def render_tier1_ipo_group(self, group, date_label, filename=None):
        return self._render_tier1_metric_group(
            group, date_label,
            accent_color=COLORS["green"],
            title="New IPO Listings",
            metric_keys=[
                ("Offer Price", "offer_price"),
                ("Offer Size", "offer_size"),
                ("Listing", "listing_date"),
                ("Market Cap", "market_cap"),
                ("Use of Funds", "use_of_funds"),
            ],
            filename=filename,
        )

    def render_tier1_buyback_group(self, group, date_label, filename=None):
        return self._render_tier1_metric_group(
            group, date_label,
            accent_color=COLORS["green"],
            title="Stock Buybacks",
            metric_keys=[
                ("Budget", "budget"),
                ("Max Price", "max_price"),
                ("Shares", "shares_target"),
                ("Duration", "duration"),
                ("% Outstanding", "pct_outstanding"),
            ],
            filename=filename,
        )

    def render_tier1_news(self, news, filename=None):
        tags = normalize_tags(news.get("tags_parsed") or [])
        template = "News - Insider Trading.png" if "Insider Trading" in tags else "IDX - News 1.png"
        image = self._open(template)
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.1)

        accent_color = COLORS["pink"] if "Insider Trading" in tags else COLORS["orange"]

        y = 360

        # Tickers at the top
        tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
        tickers = [t.strip() for t in tickers_str.split("/") if t.strip()]

        curr_x = margin
        if tickers:
            for ticker in tickers[:3]:
                curr_x = self._chip(draw, (curr_x, y), ticker, fill=accent_color, text_fill=COLORS["white"], font_size=32)
        else:
            tag = tags[0] if tags else "News"
            self._chip(draw, (curr_x, y), tag.upper(), fill=accent_color, text_fill=COLORS["white"], font_size=32)

        y += 110

        # Title - Very Bold and Large
        title_raw = str(news.get("headline") or news.get("title", "IDX News"))
        title = title_raw.replace("**", "")
        title_fnt = fit_font(draw, title, w - 2 * margin, 72, 48, bold=True)
        title_y_start = y
        y = draw_wrapped(draw, (margin, y), title, title_fnt, COLORS["ink"], w - 2 * margin, 18, 4)

        y += 40
        # Horizontal Separator
        draw.line((margin, y, margin + 250, y), fill=accent_color, width=10)
        y += 60

        # Summary / Bullets
        bullets = news.get("bullets")
        summary = news.get("summary") or news.get("description") or news.get("content") or news.get("body") or ""

        if bullets and isinstance(bullets, list):
            summary_fnt = font("Inter-Regular.ttf", 38)
            for bullet in bullets:
                # Remove markdown from bullet point
                clean_bullet = str(bullet).replace("**", "")
                # Draw bullet point
                draw.text((margin, y), "•", font=font("Inter-Bold.ttf", 38), fill=accent_color)
                y = draw_wrapped(draw, (margin + 40, y), clean_bullet, summary_fnt, COLORS["soft_ink"], w - 2 * margin - 40, 14, 3)
                y += 20
        elif summary:
            # Available height for summary: from current y to near stats bar
            available_h = (h - 400) - y
            summary_size = 40
            line_gap = 16
            while summary_size > 18:
                summary_fnt = font("Inter-Regular.ttf", summary_size)
                lines = wrap_text(draw, summary, summary_fnt, w - 2 * margin)
                total_h = len(lines) * (summary_size + line_gap)
                if total_h <= available_h:
                    break
                summary_size -= 2
                line_gap = max(4, line_gap - 2)
            summary_fnt = font("Inter-Regular.ttf", summary_size)
            y = draw_wrapped(draw, (margin, y), summary, summary_fnt, COLORS["soft_ink"], w - 2 * margin, line_gap)

        # Draw Vertical Accent Bar on the left
        draw.rounded_rectangle((margin - 35, title_y_start, margin - 15, y), radius=10, fill=accent_color)

        # Quick Stats Bar at the bottom
        self._render_quick_stats(draw, (margin, h - 350), tickers[0] if tickers else "IDX", accent_color)

        # Footer Source
        source = source_label(news.get("source") or news.get("url"))
        draw.text((margin, h - 210), f"Source: {source}", font=font("Inter-Regular.ttf", 28), fill=COLORS["muted"])

        slug = clean_slug(news.get("id") or news.get("symbol") or news.get("title") or "news")
        return self._save(image, filename or f"news_tier1_{slug}.png")
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
