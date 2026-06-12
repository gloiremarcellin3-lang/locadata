import os
from datetime import datetime
from qgis.core import QgsVectorLayer

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, HRFlowable, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


def exporter_rapport_pdf(layer, chemin, titre, poids):
    if not REPORTLAB_OK:
        _exporter_txt(layer, chemin, titre, poids)
        return chemin

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Titre1', fontSize=18, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#534AB7'), spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='Titre2', fontSize=13, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#534AB7'), spaceBefore=12, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='Corps', fontSize=9, fontName='Helvetica', spaceAfter=4
    ))

    doc = SimpleDocTemplate(
        chemin, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
        title=titre, author="Gloire Marcellin Mbamba Mouanda"
    )

    elements = []

    # En-tête
    elements.append(Paragraph(titre, styles['Titre1']))
    elements.append(Paragraph(
        "Rapport d'analyse multicritère — LocaData v1.0",
        styles['Corps']
    ))
    elements.append(Paragraph(
        f"Auteur : Gloire Marcellin Mbamba Mouanda | "
        f"Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        styles['Corps']
    ))
    elements.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#534AB7'), spaceAfter=12
    ))

    # Statistiques
    scores = [f['SC_GLOBAL'] for f in layer.getFeatures()
              if f['SC_GLOBAL'] is not None]

    if scores:
        moy  = round(sum(scores) / len(scores), 1)
        maxi = round(max(scores), 1)
        mini = round(min(scores), 1)

        elements.append(Paragraph("Synthèse des résultats", styles['Titre2']))

        data = [
            ["Indicateur", "Valeur"],
            ["Score moyen global", f"{moy} / 100"],
            ["Score maximum",      f"{maxi} / 100"],
            ["Score minimum",      f"{mini} / 100"],
            ["Nombre de zones",    str(len(scores))],
        ]
        t = Table(data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#534AB7')),
            ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
            ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, -1), 9),
            ('ALIGN',       (1, 0), (1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#f5f5f5'), colors.white]),
            ('GRID',        (0, 0), (-1, -1), 0.3,
             colors.HexColor('#dddddd')),
            ('TOPPADDING',  (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))

    # Poids utilisés
    elements.append(Paragraph("Pondérations utilisées", styles['Titre2']))
    data_poids = [["Critère", "Poids"]] + [
        [k.capitalize(), f"{v} %"] for k, v in poids.items()
    ]
    t2 = Table(data_poids, colWidths=[8*cm, 8*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#1D9E75')),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, -1), 9),
        ('ALIGN',       (1, 0), (1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor('#f5f5f5'), colors.white]),
        ('GRID',        (0, 0), (-1, -1), 0.3,
         colors.HexColor('#dddddd')),
        ('TOPPADDING',  (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 0.5*cm))

    # Référence
    elements.append(PageBreak())
    elements.append(Paragraph("Référence", styles['Titre2']))
    elements.append(Paragraph(
        "Mbamba Mouanda G. (2026). Implantation des data centers : "
        "entre dépendance numérique et acceptabilité territoriale. "
        "Mémoire M2 Géomatique, CY Cergy Paris Université.",
        styles['Corps']
    ))

    def pied(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#888780'))
        canvas.drawString(2*cm, 1.1*cm,
            "LocaData v1.0 — Gloire Mbamba, 2026")
        canvas.drawRightString(A4[0] - 2*cm, 1.1*cm,
            f"Page {doc.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=pied, onLaterPages=pied)
    return chemin


def _exporter_txt(layer, chemin, titre, poids):
    """Fallback si ReportLab n'est pas disponible."""
    chemin_txt = chemin.replace('.pdf', '.txt')
    scores = [f['SC_GLOBAL'] for f in layer.getFeatures()
              if f['SC_GLOBAL'] is not None]
    moy = round(sum(scores)/len(scores), 1) if scores else 0
    with open(chemin_txt, 'w', encoding='utf-8') as f:
        f.write(f"{titre}\n")
        f.write(f"Auteur : Gloire Marcellin Mbamba Mouanda\n")
        f.write(f"Date : {datetime.now().strftime('%d/%m/%Y')}\n\n")
        f.write(f"Score moyen : {moy} / 100\n")
        f.write(f"Zones analysées : {len(scores)}\n\n")
        f.write("Poids utilisés :\n")
        for k, v in poids.items():
            f.write(f"  {k} : {v}%\n")