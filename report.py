from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from schemas import ContextPack, DomainOutput, OrchestratorOutput, QuestionnairePack


def _bullets(items: Iterable[str]) -> str:
    values = list(items)
    if not values:
        return "-"
    return "<br/>".join(f"• {x}" for x in values)



def build_pdf_report(profile: dict, result: dict, answers: dict[str, str], generated_at: str | None = None) -> bytes:
    context: ContextPack = result["context"]
    questionnaire: QuestionnairePack = result["questionnaire"]
    cyber: DomainOutput = result["cyber"]
    rgpd: DomainOutput = result["rgpd"]
    rse: DomainOutput = result["rse"]
    orchestrator: OrchestratorOutput = result["orchestrator"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    title = styles["Title"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    body.leading = 14

    generated_label = datetime.now().strftime("%d/%m/%Y %H:%M")
    if generated_at:
        try:
            generated_label = datetime.fromisoformat(generated_at).strftime("%d/%m/%Y %H:%M")
        except Exception:
            generated_label = str(generated_at)

    story = []
    story.append(Paragraph("ComplianceAI — Rapport d'audit", title))
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            f"<b>Entreprise :</b> {profile.get('name', '-')}&nbsp;&nbsp;&nbsp; <b>Secteur :</b> {profile.get('sector', '-')}<br/>"
            f"<b>Effectif :</b> {profile.get('employees', '-')} &nbsp;&nbsp;&nbsp; <b>CA annuel :</b> {profile.get('annual_revenue', '-')} €<br/>"
            f"<b>Date :</b> {generated_label}",
            body,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    score_table = Table(
        [
            ["Score global", "CYBER", "RGPD", "RSE", "Niveau de risque"],
            [
                str(orchestrator.global_score),
                str(cyber.score),
                str(rgpd.score),
                str(rse.score),
                orchestrator.risk_level,
            ],
        ],
        colWidths=[3.1 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 4.2 * cm],
    )
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eff6ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(score_table)
    story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("1. Synthèse dirigeant", h1))
    story.append(Paragraph(orchestrator.executive_summary, body))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(f"<b>À retenir :</b> {orchestrator.business_takeaway}", body))
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            f"<b>Fourchette de risque estimative :</b> {orchestrator.financial_range_low:,} € à {orchestrator.financial_range_high:,} €".replace(",", " "),
            body,
        )
    )

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("2. Contexte d'analyse", h1))
    story.append(Paragraph(context.profile_summary, body))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(f"<b>Expositions clés :</b><br/>{_bullets(context.key_exposures)}", body))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(f"<b>Angles de questionnaire :</b><br/>{_bullets(context.questionnaire_angles)}", body))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("3. Priorités et feuille de route", h1))
    story.append(Paragraph(f"<b>Top priorités :</b><br/>{_bullets(orchestrator.top_priorities)}", body))
    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph(f"<b>30 jours :</b><br/>{_bullets(orchestrator.roadmap_30)}", body))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(f"<b>60 jours :</b><br/>{_bullets(orchestrator.roadmap_60)}", body))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(f"<b>90 jours :</b><br/>{_bullets(orchestrator.roadmap_90)}", body))
    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph(f"<b>Points de vigilance :</b><br/>{_bullets(orchestrator.watchouts)}", body))

    for block in [cyber, rgpd, rse]:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(f"4. Domaine {block.domain}", h1))
        story.append(Paragraph(f"<b>Score :</b> {block.score}/100", h2))
        story.append(Paragraph(block.summary, body))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<b>Points solides :</b><br/>{_bullets(block.strengths)}", body))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<b>Écarts visibles :</b><br/>{_bullets(block.gaps)}", body))
        story.append(Spacer(1, 0.1 * cm))
        risk_lines = []
        for risk in block.risks:
            risk_lines.append(f"• <b>{risk.severity}</b> — {risk.title} : {risk.business_impact}")
        story.append(Paragraph(f"<b>Risques importants :</b><br/>{'<br/>'.join(risk_lines) if risk_lines else '-'}", body))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<b>Quick wins :</b><br/>{_bullets(block.quick_wins)}", body))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<b>Actions recommandées :</b><br/>{_bullets(block.recommended_actions)}", body))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("5. Annexe — Questions et réponses", h1))
    rows = [["Domaine", "Question", "Réponse"]]
    for q in questionnaire.questions:
        rows.append([q.domain, q.label, answers.get(q.id, "Non")])
    qa_table = Table(rows, colWidths=[2.2 * cm, 10.0 * cm, 3.2 * cm], repeatRows=1)
    qa_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ]
        )
    )
    story.append(qa_table)

    doc.build(story)
    return buffer.getvalue()
