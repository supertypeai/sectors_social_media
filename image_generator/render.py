import ast
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKGROUND_DIR = ROOT_DIR / "background"
OUTPUT_DIR = ROOT_DIR / "output"
PERIWATCH_FONT_DIR = ROOT_DIR.parent / "periwatch_pdf_generator" / "api" / "asset" / "font"

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
        PERIWATCH_FONT_DIR / name,
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
    try:
        value = float(value)
    except Exception:
        return "-"
    if abs(value) >= 1_000_000_000_000:
        return f"IDR {value / 1_000_000_000_000:.1f}T"
    if abs(value) >= 1_000_000_000:
        return f"IDR {value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"IDR {value / 1_000_000:.1f}M"
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
        draw_wrapped(draw, (x + 34, y + 68), value, font("Inter-Bold.ttf", 38), COLORS["ink"], width - 58, 4, 2)

    def render_daily_filings(self, filings, date_label, filename="filings_daily.png"):
        image = self._open("News - Insider Trading.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.08)

        rows = list(filings)[:4]
        y = 360
        card_gap = 25
        card_h = 320

        for i, row in enumerate(rows):
            is_buy = "buy" in str(row.get("title", "")).lower() or "purchase" in str(row.get("title", "")).lower()
            accent_color = COLORS["green"] if is_buy else COLORS["red"]
            
            # Card
            self._card(draw, (margin, y, w - margin, y + card_h), radius=24, fill="#ffffff", outline="#eeeeee", width=2)
            draw.rounded_rectangle((margin, y, margin + 10, y + card_h), radius=6, fill=accent_color)

            # Logo Placeholder
            logo_x, logo_y = margin + 35, y + 35
            draw.ellipse((logo_x, logo_y, logo_x + 100, logo_y + 100), fill="#f8f8f8", outline="#eeeeee", width=1)
            symbol_raw = str(row.get("symbol", "?"))
            symbol_char = symbol_raw[:1]
            draw.text((logo_x + 35, logo_y + 20), symbol_char, font=font("Inter-Bold.ttf", 48), fill=accent_color)

            # Content Area
            inner_x = logo_x + 130
            curr_y = y + 35
            
            # Symbol & Status Chip
            symbol_text = symbol_raw
            symbol_fnt = font("Inter-Bold.ttf", 36)
            draw.text((inner_x, curr_y), symbol_text, font=symbol_fnt, fill=COLORS["ink"])
            
            status_text = "BUY" if is_buy else "SELL"
            chip_x = inner_x + draw.textlength(symbol_text, font=symbol_fnt) + 20
            # Removed the + "22" which caused issues with hex colors
            self._chip(draw, (chip_x, curr_y + 5), status_text, fill="#f0f0f0", text_fill=accent_color, font_size=24)
            
            # Holder Name
            curr_y += 55
            holder = row.get("holder_name") or "Individual/Institution"
            draw.text((inner_x, curr_y), holder, font=font("Inter-Bold.ttf", 28), fill=COLORS["soft_ink"])
            
            # Title/Context
            curr_y += 35
            context = clean_title(row.get("title", "Filing Transaction"))
            draw.text((inner_x, curr_y), context[:60] + ("..." if len(context) > 60 else ""), font=font("Inter-Regular.ttf", 24), fill=COLORS["muted"])

            # Value (Top Right)
            val_label = "Transaction Value"
            val_text = currency_idr(row.get("transaction_value", 0))
            draw.text((w - margin - 40 - draw.textlength(val_label, font=font("Inter-Regular.ttf", 22)), y + 35), val_label, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
            draw.text((w - margin - 40 - draw.textlength(val_text, font=font("Inter-Bold.ttf", 38)), y + 65), val_text, font=font("Inter-Bold.ttf", 38), fill=COLORS["ink"])

            # Divider
            draw.line((inner_x, y + 175, w - margin - 40, y + 175), fill="#eeeeee", width=1)
            
            # Metadata Row
            meta_y = y + 195
            col_w = (w - margin * 2 - 170) // 4
            
            metas = [
                ("Shares (M)", f"{row.get('share_percentage_transaction', 0):.2f}"),
                ("Price", currency_idr(row.get("price_transaction", 0))),
                ("Before", f"{row.get('share_percentage_before', 0):.2f}%"),
                ("After", f"{row.get('share_percentage_after', 0):.2f}%")
            ]
            
            for j, (label, value) in enumerate(metas):
                col_x = inner_x + (j * col_w)
                draw.text((col_x, meta_y), label, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
                draw.text((col_x, meta_y + 35), value, font=font("Inter-Bold.ttf", 28), fill=COLORS["ink"])
                
                # Add tiny arrow for "After"
                if label == "After":
                    arrow = "↗" if is_buy else "↘"
                    draw.text((col_x + draw.textlength(value, font=font("Inter-Bold.ttf", 28)) + 10, meta_y + 35), arrow, font=font("Inter-Bold.ttf", 28), fill=accent_color)

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
        title = f"{group.get('symbol')} {pattern}"
        draw_wrapped(draw, (margin, 490), title, font("Inter-Bold.ttf", 88), COLORS["ink"], w - 2 * margin, 12, 2)
        
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
        
        # Header Badge
        self._badge(draw, (margin, 380), str(important).upper(), COLORS["orange"], 30)
        
        # Title
        title = clean_title(filing.get("title", "Important Filing"))
        draw_wrapped(draw, (margin, 490), title, font("Inter-Bold.ttf", 68), COLORS["ink"], w - 2 * margin, 12, 3)
        
        y = 780
        facts = [
            ("Ticker", filing.get("symbol", "-")),
            ("Holder", filing.get("holder_name", "-")),
            ("Value", currency_idr(filing.get("transaction_value"))),
            ("Change", f"{pct(filing.get('share_percentage_before'))} -> {pct(filing.get('share_percentage_after'))}"),
        ]
        
        for label, value in facts:
            card_h = 130
            self._card(draw, (margin, y, w - margin, y + card_h), radius=20, fill="#ffffff", outline="#eeeeee", width=2)
            draw.rounded_rectangle((margin, y, margin + 8, y + card_h), radius=4, fill=COLORS["orange"])
            
            draw.text((margin + 40, y + 25), label.upper(), font=font("Inter-Bold.ttf", 22), fill=COLORS["muted"])
            draw_wrapped(draw, (margin + 320, y + 22), value, font("Inter-Bold.ttf", 36), COLORS["ink"], w - margin - 360, 4, 2)
            y += card_h + 20
            
        symbol = clean_slug(filing.get("symbol", "filing"))
        return self._save(image, filename or f"filing_tag_{symbol}_{clean_slug(important)}.png")

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
        title = clean_title(news.get("headline") or news.get("title", "IDX News"))
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
                # Draw bullet point
                draw.text((margin, y), "•", font=font("Inter-Bold.ttf", 38), fill=accent_color)
                y = draw_wrapped(draw, (margin + 40, y), bullet, summary_fnt, COLORS["soft_ink"], w - 2 * margin - 40, 14, 3)
                y += 20
        elif summary:
            # Available height for summary: from current y to near footer
            available_h = (h - 240) - y
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
