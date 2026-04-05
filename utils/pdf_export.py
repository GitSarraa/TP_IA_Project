"""
utils/pdf_export.py
Generation d'un PDF professionnel de l'itineraire.
Utilise DejaVu (fonts/ du projet) pour supporter accents et caracteres speciaux.
"""
import re
import os
from fpdf import FPDF
from datetime import datetime

# Dossier fonts/ a la racine du projet (un niveau au-dessus de utils/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS_DIR = os.path.join(_HERE, "..", "fonts")


def _font_path(filename: str) -> str:
    path = os.path.normpath(os.path.join(_FONTS_DIR, filename))
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Police introuvable : {path}\n"
            "Assurez-vous que le dossier fonts/ contient :\n"
            "  DejaVuSans.ttf, DejaVuSans-Bold.ttf, DejaVuSans-Oblique.ttf"
        )
    return path


def _strip_emoji(text: str) -> str:
    """Supprime les emojis et symboles hors Latin (DejaVu gere les accents)."""
    result = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x2000:
            result.append(ch)
        else:
            result.append(" ")
    return "".join(result).strip()


class TravelPDF(FPDF):
    def __init__(self, destination: str, days: int):
        super().__init__()
        self.destination = _strip_emoji(destination)
        self.days = days
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font("DejaVu", style="",  fname=_font_path("DejaVuSans.ttf"))
        self.add_font("DejaVu", style="B", fname=_font_path("DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", style="I", fname=_font_path("DejaVuSans-Oblique.ttf"))

    def header(self):
        self.set_fill_color(15, 20, 40)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 215, 0)
        self.set_font("DejaVu", "B", 11)
        self.set_y(4)
        self.cell(0, 10, f"TravelMind -- {self.destination.upper()}", align="C")
        self.set_text_color(0, 0, 0)
        self.ln(14)

    def footer(self):
        self.set_y(-15)
        self.set_fill_color(15, 20, 40)
        self.rect(0, 285, 210, 15, "F")
        self.set_text_color(200, 200, 200)
        self.set_font("DejaVu", "", 8)
        self.set_y(-12)
        self.cell(
            0, 8,
            f"TravelMind AI -- Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')} -- Page {self.page_no()}",
            align="C",
        )
        self.set_text_color(0, 0, 0)


def generate_pdf(itinerary: str, destination: str, days: int, travelers: int, budget: str) -> bytes:
    pdf = TravelPDF(destination, days)
    pdf.add_page()

    pdf.set_fill_color(15, 20, 40)
    pdf.rect(10, 22, 190, 30, "F")
    pdf.set_text_color(255, 215, 0)
    pdf.set_font("DejaVu", "B", 20)
    pdf.set_y(26)
    pdf.cell(0, 10, f"Voyage a {_strip_emoji(destination)}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(180, 210, 255)
    pdf.cell(0, 8, f"{days} jours  |  {travelers} voyageur(s)  |  Budget: {_strip_emoji(budget)}/pers/jour",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    _render_lines(pdf, _clean_markdown(itinerary))

    pdf.ln(5)
    y = pdf.get_y()
    if y + 14 > 270:
        pdf.add_page()
        y = pdf.get_y()
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(15, 20, 40)
    pdf.rect(10, y, 190, 14, "FD")
    pdf.set_font("DejaVu", "I", 9)
    pdf.set_text_color(80, 80, 120)
    pdf.set_y(y + 4)
    pdf.cell(0, 6, "Itineraire genere par TravelMind -- Agent IA (ReAct + Chain of Thought)", align="C")

    return bytes(pdf.output())


def _clean_markdown(text: str) -> list:
    lines = []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            lines.append(("space", ""))
        elif re.match(r"^#{1,2}\s", line):
            lines.append(("h1", _strip_emoji(re.sub(r"^#{1,2}\s*", "", line))))
        elif re.match(r"^#{3,}\s", line):
            lines.append(("h2", _strip_emoji(re.sub(r"^#{3,}\s*", "", line))))
        elif re.match(r"^[-*]\s", line):
            lines.append(("bullet", _strip_emoji(re.sub(r"^[-*]\s*", "- ", line))))
        elif re.match(r"^\*\*.*\*\*", line):
            lines.append(("bold", _strip_emoji(re.sub(r"\*\*", "", line))))
        else:
            lines.append(("text", _strip_emoji(re.sub(r"\*\*?(.*?)\*\*?", r"\1", line))))
    return lines


def _render_lines(pdf: TravelPDF, lines: list):
    for typ, content in lines:
        if not content and typ != "space":
            continue
        if typ == "space":
            pdf.ln(3)
        elif typ == "h1":
            pdf.ln(4)
            pdf.set_fill_color(15, 20, 40)
            pdf.set_text_color(255, 215, 0)
            pdf.set_font("DejaVu", "B", 13)
            pdf.set_x(10)
            pdf.cell(190, 9, f"  {content}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
        elif typ == "h2":
            pdf.ln(2)
            pdf.set_fill_color(220, 235, 255)
            pdf.set_text_color(15, 20, 80)
            pdf.set_font("DejaVu", "B", 11)
            pdf.set_x(10)
            pdf.cell(190, 7, f"  {content}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
        elif typ == "bold":
            pdf.set_font("DejaVu", "B", 10)
            pdf.set_text_color(30, 60, 120)
            pdf.set_x(15)
            pdf.multi_cell(180, 6, content)
            pdf.set_text_color(0, 0, 0)
        elif typ == "bullet":
            pdf.set_font("DejaVu", "", 9)
            pdf.set_x(20)
            pdf.multi_cell(175, 5, content)
        else:
            pdf.set_font("DejaVu", "", 9)
            pdf.set_x(15)
            if content.strip():
                pdf.multi_cell(180, 5, content)
