import os
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from image_generator.render import SocialImageRenderer, COLORS, font


ACCENT_COLOR = "#2596be"

CX0 = 110
CX1 = 978   # 1088 - 110
LOGO_R = 48
BADGE_Y = 210
FOOTER_Y = 1800
BULLET_GAP = 22
F_NAME = 46
F_DATE = 28
F_BODY = 34


def _rich_text_height(text, f_reg, f_bold, max_w, line_h):
    tokens = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        for w in part.split():
            if tokens and re.match(r'^[,\.;:\)]+$', w):
                tokens[-1] = (tokens[-1][0] + w, tokens[-1][1])
            else:
                tokens.append((w, i % 2 == 1))
    sp_w = f_reg.getbbox(" ")[2]
    lines, cur_w = 1, 0
    for j, (word, bold) in enumerate(tokens):
        ww = (f_bold if bold else f_reg).getbbox(word)[2]
        if j > 0:
            if cur_w + sp_w + ww > max_w:
                lines += 1
                cur_w = ww
            else:
                cur_w += sp_w + ww
        else:
            cur_w = ww
    return lines * line_h


def _fit_body_size(bullets, bullet_indent, avail_h, max_size=F_BODY):
    text_w = CX1 - CX0 - bullet_indent
    for size in range(max_size, 16, -1):
        f_reg = font("Inter-Regular.ttf", size)
        f_bold = font("Inter-Bold.ttf", size)
        line_h = int(size * 1.5)
        total = sum(_rich_text_height(b, f_reg, f_bold, text_w, line_h) for b in bullets)
        total += (len(bullets) - 1) * BULLET_GAP
        if total <= avail_h:
            return size, line_h
    return 16, int(16 * 1.5)


def _rich_draw(draw, x0, y0, text, max_w, f_reg, f_bold, line_h, fill):
    tokens = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        for w in part.split():
            if tokens and re.match(r'^[,\.;:\)]+$', w):
                tokens[-1] = (tokens[-1][0] + w, tokens[-1][1])
            else:
                tokens.append((w, i % 2 == 1))
    sp_w = draw.textbbox((0, 0), " ", font=f_reg)[2]
    lines, cur, cur_w = [], [], 0
    for word, bold in tokens:
        ww = draw.textbbox((0, 0), word, font=(f_bold if bold else f_reg))[2]
        if cur and cur_w + sp_w + ww > max_w:
            lines.append(cur)
            cur, cur_w = [(word, bold)], ww
        else:
            if cur:
                cur_w += sp_w
            cur.append((word, bold))
            cur_w += ww
    if cur:
        lines.append(cur)
    cy = y0
    for line in lines:
        cx = x0
        for j, (word, bold) in enumerate(line):
            f = f_bold if bold else f_reg
            if j > 0:
                cx += draw.textbbox((0, 0), " ", font=f_reg)[2]
            draw.text((cx, cy), word, fill=fill, font=f)
            cx += draw.textbbox((0, 0), word, font=f)[2]
        cy += line_h
    return cy


class AGMRenderer(SocialImageRenderer):

    def get_background(self):
        return self._open("agm.png")

    @staticmethod
    def summarize_agendas(summary: str) -> list[str]:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You paraphrase AGM (Annual General Meeting) result minutes into bullet points.\n\n"
                        "STRICT FACTUAL RULES — any violation is a critical failure:\n"
                        "- Use ONLY facts explicitly stated in the source text below.\n"
                        "- Do NOT add, infer, guess, or invent any name, number, date, percentage, "
                        "person, role, decision, or agenda item that is not written verbatim in the source.\n"
                        "- Do NOT fill in 'typical' AGM topics (dividends, auditor, board changes, etc.) "
                        "if the source does not mention them. Missing topics stay missing.\n"
                        "- Do NOT use vague filler like 'other matters were discussed' or "
                        "'various resolutions were approved' if those matters are not specified in the source.\n"
                        "- If you are unsure whether something is in the source, leave it out.\n\n"
                        "OUTPUT FORMAT:\n"
                        "- Produce at most **5 bullets**, selecting only the most important agenda items. "
                        "Priority order: (1) financial results & profit allocation, (2) dividends, "
                        "(3) board/auditor appointments, (4) other material corporate actions.\n"
                        "- EXCLUDE remuneration, honorarium, or salary-setting items entirely.\n"
                        "- If the source has fewer than 5 distinct items, produce only as many as exist — do not pad.\n"
                        "- Each bullet: plain English paraphrase, 1–2 sentences, max 35 words.\n"
                        "- Wrap key figures, names, percentages, and resolution outcomes in **double asterisks**.\n"
                        "- Start each bullet with '•' on its own line. No headers, no preamble, no closing text.\n"
                    ),
                },
                {"role": "user", "content": summary},
            ],
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        return [
            line.strip().lstrip("•").strip()
            for line in text.split("\n")
            if line.strip().startswith("•")
        ]

    def _render_card(self, company_name: str, agm_date: str, bullets: list[str], sym: str = "") -> Image.Image:
        bg = self.get_background()
        draw = ImageDraw.Draw(bg)

        try:
            fmt_date = datetime.strptime(agm_date, "%Y-%m-%d").strftime("%B %d, %Y")
        except Exception:
            fmt_date = agm_date

        logo_d = LOGO_R * 2
        header_y = BADGE_Y + 18

        name_size = F_NAME
        while name_size > 16:
            f_name = font("Inter-Bold.ttf", name_size)
            if draw.textbbox((0, 0), company_name, font=f_name)[2] <= CX1 - (CX0 + logo_d + 24):
                break
            name_size -= 1

        f_name = font("Inter-Bold.ttf", name_size)
        f_date = font("Inter-Regular.ttf", F_DATE)

        nbb = draw.textbbox((0, 0), company_name, font=f_name)
        dbb = draw.textbbox((0, 0), fmt_date, font=f_date)
        name_h = nbb[3] - nbb[1]
        date_h = dbb[3] - dbb[1]
        block_h = max(logo_d, name_h + 10 + date_h)
        logo_y = header_y + (block_h - logo_d) // 2

        self._logo(bg, (CX0, logo_y), sym, size=logo_d, accent=COLORS["orange_deep"])
        draw = ImageDraw.Draw(bg)

        tx = CX0 + logo_d + 24
        ty = header_y + (block_h - name_h - 10 - date_h) // 2
        draw.text((tx, ty), company_name, fill=COLORS["heading"], font=f_name)
        draw.text((tx, ty + name_h + 20), fmt_date, fill=COLORS["dark"], font=f_date)

        div_y = header_y + block_h + 18
        draw.line([(CX0, div_y), (CX1, div_y)], fill="#d2d5dc", width=2)

        f_bullet = font("Inter-Bold.ttf", F_BODY + 6)
        bbb = draw.textbbox((0, 0), "•", font=f_bullet)
        bullet_w = bbb[2] - bbb[0] + 14

        body_start = div_y + 28
        size, line_h = _fit_body_size(bullets, bullet_w, FOOTER_Y - body_start)
        f_body = font("Inter-Regular.ttf", size)
        f_bold = font("Inter-Bold.ttf", size)

        cy = body_start
        for item in bullets:
            body_bb = draw.textbbox((0, 0), "A", font=f_body)
            bullet_bb = draw.textbbox((0, 0), "•", font=f_bullet)
            body_ink = body_bb[3] - body_bb[1]
            bullet_ink = bullet_bb[3] - bullet_bb[1]
            bullet_y = (cy + (body_bb[1] - bullet_bb[1]) + (body_ink - bullet_ink) // 2) + 5

            draw.text((CX0, bullet_y), "•", fill=ACCENT_COLOR, font=f_bullet)
            cy = _rich_draw(
                draw, CX0 + bullet_w, cy, item,
                CX1 - CX0 - bullet_w, f_body, f_bold, line_h, COLORS["heading"],
            )
            cy += BULLET_GAP

        return bg

    def render_one(self, row: dict) -> Path:
        sym = str(row["symbol"]).replace(".JK", "")
        company_name = str(row["company_name"])
        agm_date = str(row["agm_date"])
        print(f"Summarizing AGM for {sym}...")
        bullets = self.summarize_agendas(str(row["summary"]))
        img = self._render_card(company_name, agm_date, bullets, sym)
        return self._save(img, f"agm_{sym}.png")

    def render(self, data) -> list[Path]:
        rows = data if isinstance(data, list) else data.to_dict("records")
        paths = []
        for row in rows:
            paths.append(self.render_one(row))
        return paths
