from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def create_plots(df):
    import seaborn as sns
    sns.set_style('whitegrid')

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(df['rate'], bins=20, kde=True, color='#2ABB00', ax=ax)
    ax.set_title('Распределение процентных ставок', fontsize=16, weight='bold', color='#2ABB00')
    ax.set_xlabel('Ставка (%)', fontsize=14)
    ax.set_ylabel('Количество вкладов', fontsize=14)
    plt.tight_layout()
    buf1 = BytesIO()
    plt.savefig(buf1, format='PNG', dpi=150)
    plt.close(fig)
    buf1.seek(0)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(df['term_months'], bins=20, kde=True, color='#2ABB00', ax=ax)
    ax.set_title('Распределение сроков (месяцы)', fontsize=16, weight='bold', color='#2ABB00')
    ax.set_xlabel('Срок (мес.)', fontsize=14)
    ax.set_ylabel('Количество вкладов', fontsize=14)
    plt.tight_layout()
    buf2 = BytesIO()
    plt.savefig(buf2, format='PNG', dpi=150)
    plt.close(fig)
    buf2.seek(0)

    return buf1, buf2

def generate_pdf_report(csv_path, output_path):
    df = pd.read_csv(csv_path)

    font_path = Path(__file__).parent / "DejaVuSerif.ttf"  # Путь к TTF-шрифту (укажи, где у тебя лежит файл)
    pdfmetrics.registerFont(TTFont('DejaVuSerif', str(font_path)))

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    c.setFont("DejaVuSerif", 20)
    c.drawString(50, height - 50, "Отчёт по вкладам Сбербанка")

    c.setFont("DejaVuSerif", 12)
    c.drawString(50, height - 80, f"Всего записей: {len(df)}")

    c.drawString(50, height - 110, "Основные графики:")

    buf1, buf2 = create_plots(df)

    img1 = ImageReader(buf1)
    c.drawImage(img1, 50, height - 370, width=500, height=200)

    img2 = ImageReader(buf2)
    c.drawImage(img2, 50, height - 600, width=500, height=200)

    c.save()
    print(f"Отчёт сохранён в {output_path}")

if __name__ == "__main__":
    generate_pdf_report("../data/clean/clean_deposits.csv", "report.pdf")