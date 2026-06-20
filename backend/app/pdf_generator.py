from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as ReportLabImage,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from PIL import Image as PILImage, ImageDraw, ImageFont
import io
import os
from typing import Any


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(BASE_DIR, 'fonts')

# Font files are not committed by default.
# Add NanumGothic.ttf and NanumGothicBold.ttf to backend/fonts/ for Korean PDF rendering.
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
try:
    regular_font = os.path.join(FONT_PATH, 'NanumGothic.ttf')
    bold_font = os.path.join(FONT_PATH, 'NanumGothicBold.ttf')
    if os.path.exists(regular_font) and os.path.exists(bold_font):
        pdfmetrics.registerFont(TTFont('NanumGothic', regular_font))
        pdfmetrics.registerFont(TTFont('NanumGothicBold', bold_font))
        FONT_REGULAR = 'NanumGothic'
        FONT_BOLD = 'NanumGothicBold'
except Exception:
    # Fall back to built-in ReportLab fonts so the API can still start.
    pass

def risk_label(score: float) -> str:
    if score >= 80:
        return '긴급'
    if score >= 60:
        return '높음'
    if score >= 30:
        return '주의'
    return '낮음'


def draw_detection_boxes(image_bytes: bytes, detections: list[dict[str, Any]]) -> bytes:
    """
    Draw YOLO bounding boxes on the uploaded image for PDF evidence preview.
    Uses PIL only to keep deployment lightweight.
    """
    img = PILImage.open(io.BytesIO(image_bytes)).convert('RGB')

    if not detections:
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=90)
        return output.getvalue()

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(os.path.join(FONT_PATH, 'NanumGothicBold.ttf'), 22)
    except Exception:
        font = ImageFont.load_default()

    for index, item in enumerate(detections, start=1):
        bbox = item.get('bbox')
        if not bbox or len(bbox) < 4:
            continue

        x1, y1, x2, y2 = [float(v) for v in bbox]
        label = f"#{index} {item.get('class_name', 'object')} {item.get('confidence', 0) * 100:.1f}%"

        # Draw a red box and readable label.
        draw.rectangle([x1, y1, x2, y2], outline=(255, 59, 48), width=5)

        label_box = draw.textbbox((x1, y1), label, font=font)
        label_width = label_box[2] - label_box[0]
        label_height = label_box[3] - label_box[1]
        label_y1 = max(0, y1 - label_height - 10)
        label_y2 = label_y1 + label_height + 8

        draw.rectangle(
            [x1, label_y1, x1 + label_width + 12, label_y2],
            fill=(255, 59, 48)
        )
        draw.text((x1 + 6, label_y1 + 4), label, fill=(255, 255, 255), font=font)

    output = io.BytesIO()
    img.save(output, format='JPEG', quality=90)
    return output.getvalue()


def generate_evidence_pdf(
    image_bytes: bytes,
    hash_value: str,
    timestamp: str,
    latitude: float | None,
    longitude: float | None,
    confidence: float,
    damage_score: float,
    detected: bool,
    gps_accuracy_m: float | None = None,
    bbox: list[float] | None = None,
    detections: list[dict[str, Any]] | None = None,
    detection_count: int = 0,
    model_version: str = 'unknown',
    threshold: float = 0.0,
    analysis_id: str | None = None,
) -> bytes:

    detections = detections or []
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    elements = []

    title_style = ParagraphStyle(
        'Title',
        fontName=FONT_BOLD,
        fontSize=20,
        alignment=1,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'Normal',
        fontName=FONT_REGULAR,
        fontSize=10,
        spaceAfter=4
    )
    bold_style = ParagraphStyle(
        'Bold',
        fontName=FONT_BOLD,
        fontSize=10,
        spaceAfter=4
    )
    small_style = ParagraphStyle(
        'Small',
        fontName=FONT_REGULAR,
        fontSize=8,
        spaceAfter=4,
        leading=12
    )

    elements.append(Paragraph('Road-Insight 도로 위험 분석 리포트', title_style))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph('AI 기반 도로 위험 요소 분석 및 신고 보조 리포트', normal_style))
    elements.append(Spacer(1, 0.3 * cm))

    elements.append(Table(
        [['']],
        colWidths=[17 * cm],
        style=TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#1D9E75')),
        ])
    ))
    elements.append(Spacer(1, 0.3 * cm))

    result_text = '도로 위험 요소 감지됨' if detected else '포트홀 미감지'
    result_color = '#A32D2D' if detected else '#085041'
    elements.append(Paragraph(f'<font color="{result_color}"><b>탐지 결과: {result_text}</b></font>', bold_style))
    elements.append(Spacer(1, 0.3 * cm))

    analysis_data = [
        ['항목', '내용'],
        ['분석 ID', analysis_id or '없음'],
        ['탐지 객체 수', f'{detection_count}건'],
        ['대표 AI 신뢰도', f'{confidence * 100:.1f}%'],
        ['신뢰도 기준', f'{threshold * 100:.0f}% 이상' if threshold else '미표시'],
        ['대표 위험도 점수', f'{damage_score:.1f} / 100 ({risk_label(damage_score)})'],
        ['모델 버전', model_version],
        ['분석 시각', timestamp],
        ['GPS 위도', str(latitude) if latitude is not None else '없음'],
        ['GPS 경도', str(longitude) if longitude is not None else '없음'],
        ['GPS 정확도', f'±{gps_accuracy_m:.0f}m' if gps_accuracy_m is not None else '없음'],
    ]

    analysis_table = Table(
        analysis_data,
        colWidths=[5 * cm, 12 * cm],
        style=TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D9E75')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])
    )
    elements.append(analysis_table)
    elements.append(Spacer(1, 0.5 * cm))

    if detections:
        elements.append(Paragraph('탐지 객체 목록', bold_style))
        detection_rows = [['#', '유형', '신뢰도', '면적 비율', '위험도']]
        for index, item in enumerate(detections, start=1):
            detection_rows.append([
                str(index),
                item.get('class_name', 'unknown'),
                f"{item.get('confidence', 0) * 100:.1f}%",
                f"{item.get('area_ratio', 0) * 100:.2f}%",
                f"{item.get('risk_score', 0):.1f} ({risk_label(float(item.get('risk_score', 0)))})"
            ])

        detection_table = Table(
            detection_rows,
            colWidths=[1.2 * cm, 4.3 * cm, 3.0 * cm, 3.0 * cm, 5.5 * cm],
            style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#085041')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
                ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(detection_table)
        elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph('촬영 이미지 및 AI 탐지 위치', bold_style))
    elements.append(Spacer(1, 0.3 * cm))
    annotated_bytes = draw_detection_boxes(image_bytes, detections)
    img_buffer = io.BytesIO(annotated_bytes)
    img = ReportLabImage(img_buffer, width=12 * cm, height=8 * cm)
    elements.append(img)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph('무결성 검증', bold_style))
    elements.append(Spacer(1, 0.3 * cm))

    integrity_data = [
        ['항목', '내용'],
        ['분석 ID', analysis_id or '없음'],
        ['SHA-256 해시', hash_value[:32] + '...'],
        ['전체 해시값', hash_value],
        ['서버 타임스탬프', timestamp],
        ['모델 버전', model_version],
    ]

    integrity_table = Table(
        integrity_data,
        colWidths=[5 * cm, 12 * cm],
        style=TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D9E75')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])
    )
    elements.append(integrity_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Table(
        [['']],
        colWidths=[17 * cm],
        style=TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
        ])
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        '본 문서는 신고 및 사고 정리 보조를 위한 AI 분석 결과입니다. '
        '원본 이미지의 SHA-256 해시를 통해 위변조 여부를 검증할 수 있습니다. '
        '최종 판단 및 행정·법적 활용 여부는 관련 기관 또는 전문가 검토에 따릅니다.',
        small_style
    ))

    doc.build(elements)
    return buffer.getvalue()
