from __future__ import annotations

from datetime import datetime

import streamlit as st

from backend import DEFAULT_MODEL, generate_context_pack, generate_questionnaire, run_full_assessment
from report import build_pdf_report
from schemas import QuestionItem

st.set_page_config(page_title="ComplianceAI Studio", page_icon="🧭", layout="wide")

CUSTOM_CSS = """
<style>
:root {
    --bg: #f8fafc;
    --card: rgba(255,255,255,0.88);
    --line: #dbe3ef;
    --ink: #0f172a;
    --muted: #475569;
    --accent: #2563eb;
    --accent-soft: #eff6ff;
}
.main .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
html, body, [data-testid="stAppViewContainer"] {background: linear-gradient(180deg,#f8fbff 0%,#f6f7fb 45%,#f8fafc 100%);}
[data-testid="stSidebar"] {background: linear-gradient(180deg, #0f172a 0%, #111827 100%);}
[data-testid="stSidebar"] * {color: #e5eefb !important;}
.card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 1rem 1.1rem;
    box-shadow: 0 10px 30px rgba(15,23,42,0.06);
}
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 65%, #38bdf8 100%);
    color: white;
    border-radius: 28px;
    padding: 1.5rem 1.4rem;
    box-shadow: 0 18px 40px rgba(29,78,216,0.18);
}
.kpi {
    background: white;
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.9rem 1rem;
    min-height: 102px;
}
.kpi h4 {margin: 0; font-size: 0.95rem; color: var(--muted); font-weight: 600;}
.kpi p {margin: 0.35rem 0 0; font-size: 1.7rem; font-weight: 800; color: var(--ink);}
.badge {
    display:inline-block;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.82rem;
    font-weight: 700;
    margin-right: 0.35rem;
    margin-bottom: 0.35rem;
}
.section-title {font-size: 1.15rem; font-weight: 800; color: var(--ink); margin-bottom: 0.6rem;}
.small-muted {color: var(--muted); font-size: 0.92rem;}
</style>
"""


DEFAULT_PROFILE = {
    "name": "Nova Conseil",
    "sector": "Services",
    "employees": 28,
    "annual_revenue": 1800000,
    "business_model": "B2B",
    "customer_type": "entreprises",
    "data_sensitivity": "moyen",
    "remote_work": "hybride",
    "supplier_dependency": "moyenne",
    "international": "non",
    "target_score": 85,
}

ANSWER_OPTIONS = ["Oui", "Partiellement", "Non"]
SECTORS = ["Services","Commerce","E-commerce","Industrie","Santé","Finance","Éducation","Transport / Logistique","BTP / Construction","Technologie / Informatique","Secteur public","Autre"]
BUSINESS_MODELS = ["B2B", "B2C", "B2B et B2C"]
CUSTOMERS = ["entreprises", "grand public", "mixte"]
SENSITIVITY = ["faible", "moyen", "élevé", "très élevé"]
REMOTE = ["principalement sur site", "hybride", "majoritairement à distance"]
SUPPLIERS = ["faible", "moyenne", "forte"]
YES_NO = ["non", "oui"]


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("page", "Accueil")
    ss.setdefault("profile", DEFAULT_PROFILE.copy())
    ss.setdefault("context", None)
    ss.setdefault("questionnaire", None)
    ss.setdefault("answers", {})
    ss.setdefault("result", None)
    ss.setdefault("generated_at", None)


init_state()
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)



def get_questions(domain: str | None = None) -> list[QuestionItem]:
    questionnaire = st.session_state.questionnaire
    if not questionnaire:
        return []
    if domain is None:
        return list(questionnaire.questions)
    return [q for q in questionnaire.questions if q.domain == domain]



def refresh_questionnaire(force: bool = False) -> None:
    if st.session_state.questionnaire is not None and not force:
        return
    context, _ = generate_context_pack(st.session_state.profile, model=DEFAULT_MODEL)
    questionnaire, _ = generate_questionnaire(st.session_state.profile, context, model=DEFAULT_MODEL)
    st.session_state.context = context
    st.session_state.questionnaire = questionnaire
    st.session_state.answers = {q.id: st.session_state.answers.get(q.id, "Non") for q in questionnaire.questions}
    st.session_state.result = None


with st.sidebar:
    st.markdown("## ComplianceAI")
    st.caption("Pilotage conformité, cyber et RSE")
    page = st.radio(
        "Navigation",
        options=["Accueil", "Profil", "Diagnostic", "Résultats"],
        index=["Accueil", "Profil", "Diagnostic", "Résultats"].index(st.session_state.page),
        label_visibility="collapsed",
    )
    st.session_state.page = page
    st.divider()
    profile = st.session_state.profile
    st.markdown("### Vue rapide")
    st.write(f"**{profile['name']}**")
    st.write(f"Secteur : {profile['sector']}")
    st.write(f"Effectif : {profile['employees']}")
    st.write(f"Modèle : {profile['business_model']}")
    st.write(f"Données : {profile['data_sensitivity']}")
    st.write(f"Travail : {profile['remote_work']}")
    st.divider()
    if st.button("Régénérer le diagnostic", use_container_width=True):
        st.session_state.questionnaire = None
        st.session_state.context = None
        st.session_state.result = None
        st.session_state.answers = {}
        if st.session_state.page != "Profil":
            st.session_state.page = "Profil"
        st.rerun()


if st.session_state.page == "Accueil":
    left, right = st.columns([1.6, 1.0], gap="large")
    with left:
        st.markdown(
            """
            <div class="hero">
                <div style="font-size:0.85rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;opacity:.88;">Diagnostic adaptatif</div>
                <h1 style="margin:0.4rem 0 0.4rem;font-size:2.15rem;line-height:1.05;">Une expérience claire côté dirigeant, un moteur d'analyse invisible derrière.</h1>
                <p style="margin:0;font-size:1rem;opacity:.95;max-width:740px;">Le questionnaire se calibre selon le profil saisi. La restitution met l'accent sur les écarts concrets, les priorités et la feuille de route.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        c1, c2, c3 = st.columns(3)
        for col, title, text in [
            (c1, "Profil ciblé", "Le cadrage prend en compte secteur, taille, exposition données et mode de travail."),
            (c2, "Diagnostic utile", "Les questions cherchent des éléments visibles et actionnables, pas de la théorie."),
            (c3, "Restitution dirigeant", "Synthèse, priorités, roadmaps 30/60/90 et rapport PDF complet."),
        ]:
            with col:
                st.markdown(f"<div class='card'><div class='section-title'>{title}</div><div class='small-muted'>{text}</div></div>", unsafe_allow_html=True)
        if st.button("Configurer le profil", type="primary"):
            st.session_state.page = "Profil"
            st.rerun()
    with right:
        st.markdown("<div class='card'><div class='section-title'>Ce que tu obtiens</div>"
                    "<span class='badge'>Questionnaire adaptatif</span>"
                    "<span class='badge'>Dashboard clair</span>"
                    "<span class='badge'>Rapport PDF</span>"
                    "<span class='badge'>Priorités</span>"
                    "<span class='badge'>Roadmap</span>"
                    "<p class='small-muted' style='margin-top:0.8rem;'>L'interface reste volontairement sobre : elle montre le diagnostic, pas la mécanique technique.</p></div>", unsafe_allow_html=True)
        st.write("")
        st.markdown("<div class='card'><div class='section-title'>Parcours</div><ol class='small-muted' style='padding-left:1.2rem;'>"
                    "<li>Compléter le profil</li><li>Générer le questionnaire</li><li>Répondre en quelques minutes</li><li>Lire la synthèse et exporter le rapport</li></ol></div>", unsafe_allow_html=True)

elif st.session_state.page == "Profil":
    st.markdown("## Profil entreprise")
    st.caption("Les informations ci-dessous servent à ajuster le diagnostic et la restitution.")
    c1, c2, c3 = st.columns(3)
    with c1:
        name = st.text_input("Nom de l'entreprise", value=st.session_state.profile["name"])
        sector = st.selectbox("Secteur", SECTORS, index=SECTORS.index(st.session_state.profile["sector"]))
        employees = st.number_input("Effectif", min_value=1, max_value=100000, value=int(st.session_state.profile["employees"]), step=1)
        annual_revenue = st.number_input("CA annuel estimé (€)", min_value=0, value=int(st.session_state.profile["annual_revenue"]), step=10000)
    with c2:
        business_model = st.selectbox("Modèle économique", BUSINESS_MODELS, index=BUSINESS_MODELS.index(st.session_state.profile["business_model"]))
        customer_type = st.selectbox("Type de clientèle", CUSTOMERS, index=CUSTOMERS.index(st.session_state.profile["customer_type"]))
        data_sensitivity = st.selectbox("Sensibilité des données", SENSITIVITY, index=SENSITIVITY.index(st.session_state.profile["data_sensitivity"]))
        remote_work = st.selectbox("Mode de travail", REMOTE, index=REMOTE.index(st.session_state.profile["remote_work"]))
    with c3:
        supplier_dependency = st.selectbox("Dépendance fournisseurs", SUPPLIERS, index=SUPPLIERS.index(st.session_state.profile["supplier_dependency"]))
        international = st.selectbox("Activité internationale", YES_NO, index=YES_NO.index(st.session_state.profile["international"]))
        target_score = st.slider("Niveau visé", 55, 95, int(st.session_state.profile["target_score"]))
        st.write("")
        st.markdown("<div class='card'><div class='section-title'>Conseil</div><div class='small-muted'>Sois réaliste sur les volumes et la sensibilité des données : c'est ce qui influence le plus l'angle du diagnostic.</div></div>", unsafe_allow_html=True)

    if st.button("Générer le questionnaire", type="primary"):
        st.session_state.profile = {
            "name": name,
            "sector": sector,
            "employees": int(employees),
            "annual_revenue": int(annual_revenue),
            "business_model": business_model,
            "customer_type": customer_type,
            "data_sensitivity": data_sensitivity,
            "remote_work": remote_work,
            "supplier_dependency": supplier_dependency,
            "international": international,
            "target_score": int(target_score),
        }
        with st.spinner("Préparation du diagnostic…"):
            refresh_questionnaire(force=True)
        st.session_state.page = "Diagnostic"
        st.rerun()

elif st.session_state.page == "Diagnostic":
    if st.session_state.questionnaire is None:
        refresh_questionnaire(force=True)
    context = st.session_state.context
    questionnaire = st.session_state.questionnaire

    st.markdown("## Diagnostic")
    st.caption(questionnaire.intro)
    c1, c2 = st.columns([1.5, 1.0])
    with c1:
        st.markdown("<div class='card'><div class='section-title'>Contexte retenu</div>"
                    f"<div class='small-muted'>{context.profile_summary}</div>"
                    f"<div style='margin-top:.7rem'>{''.join([f'<span class=\'badge\'>{x}</span>' for x in context.key_exposures[:5]])}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'><div class='section-title'>Angles d'analyse</div>"
                    f"<div class='small-muted'>{'<br/>'.join('• ' + x for x in context.questionnaire_angles[:4])}</div></div>", unsafe_allow_html=True)

    tabs = st.tabs(["Cybersécurité", "RGPD", "RSE"])
    for tab, domain, label in zip(tabs, ["CYBER", "RGPD", "RSE"], ["Cybersécurité", "RGPD", "RSE"]):
        with tab:
            for q in get_questions(domain):
                current = st.session_state.answers.get(q.id, "Non")
                st.markdown(f"<div class='card'><div class='section-title'>{q.label}</div><div class='small-muted'>{q.help_text}</div></div>", unsafe_allow_html=True)
                st.session_state.answers[q.id] = st.radio(
                    f"Réponse — {q.id}",
                    options=ANSWER_OPTIONS,
                    index=ANSWER_OPTIONS.index(current),
                    horizontal=True,
                    key=f"ans_{q.id}",
                    label_visibility="collapsed",
                )
                with st.expander("Pourquoi cette question ?"):
                    st.write(q.rationale)

    if st.button("Lancer l'analyse", type="primary"):
        with st.spinner("Analyse en cours…"):
            st.session_state.result = run_full_assessment(st.session_state.profile, st.session_state.answers, model=DEFAULT_MODEL)
            st.session_state.generated_at = datetime.now().isoformat()
        st.session_state.page = "Résultats"
        st.rerun()

elif st.session_state.page == "Résultats":
    if st.session_state.result is None:
        st.info("Aucune analyse disponible pour le moment.")
        if st.button("Aller au diagnostic"):
            st.session_state.page = "Diagnostic"
            st.rerun()
        st.stop()

    result = st.session_state.result
    orchestrator = result["orchestrator"]
    cyber = result["cyber"]
    rgpd = result["rgpd"]
    rse = result["rse"]

    st.markdown("## Résultats")
    top1, top2, top3, top4 = st.columns(4)
    for col, title, value in [
        (top1, "Score global", f"{orchestrator.global_score}/100"),
        (top2, "Cyber", f"{cyber.score}/100"),
        (top3, "RGPD", f"{rgpd.score}/100"),
        (top4, "RSE", f"{rse.score}/100"),
    ]:
        with col:
            st.markdown(f"<div class='kpi'><h4>{title}</h4><p>{value}</p></div>", unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1.5, 1.0], gap="large")
    with left:
        st.markdown(f"<div class='card'><div class='section-title'>Synthèse dirigeant</div><div class='small-muted'>{orchestrator.executive_summary}</div></div>", unsafe_allow_html=True)
        st.write("")
        st.markdown(f"<div class='card'><div class='section-title'>Lecture métier</div><div class='small-muted'>{orchestrator.business_takeaway}</div></div>", unsafe_allow_html=True)
        st.write("")
        st.markdown("### Priorités")
        for item in orchestrator.top_priorities:
            st.write(f"- {item}")
        st.markdown("### Roadmap 30 / 60 / 90 jours")
        r1, r2, r3 = st.columns(3)
        for col, title, items in [(r1, "30 jours", orchestrator.roadmap_30), (r2, "60 jours", orchestrator.roadmap_60), (r3, "90 jours", orchestrator.roadmap_90)]:
            with col:
                st.markdown(f"<div class='card'><div class='section-title'>{title}</div><div class='small-muted'>{'<br/>'.join('• ' + x for x in items) if items else '—'}</div></div>", unsafe_allow_html=True)
    with right:
        st.markdown(f"<div class='card'><div class='section-title'>Niveau de risque</div><div class='small-muted'><b>{orchestrator.risk_level.capitalize()}</b></div>"
                    f"<div class='small-muted' style='margin-top:.55rem;'>Fourchette d'exposition estimative : <b>{orchestrator.financial_range_low:,} € à {orchestrator.financial_range_high:,} €</b></div>"
                    f"<div class='small-muted' style='margin-top:.55rem;'>{'<br/>'.join('• ' + x for x in orchestrator.watchouts)}</div></div>".replace(',', ' '), unsafe_allow_html=True)
        st.write("")
        pdf_bytes = build_pdf_report(st.session_state.profile, result, st.session_state.answers, generated_at=st.session_state.generated_at)
        st.download_button(
            "Télécharger le rapport PDF",
            data=pdf_bytes,
            file_name=f"complianceai_{st.session_state.profile['name'].replace(' ', '_').lower()}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
        st.caption(f"Diagnostic généré le {datetime.fromisoformat(st.session_state.generated_at).strftime('%d/%m/%Y à %H:%M') if st.session_state.generated_at else '-'}")

    st.markdown("### Détail par domaine")
    for block, label in [(cyber, "Cybersécurité"), (rgpd, "RGPD"), (rse, "RSE")]:
        with st.expander(f"{label} — {block.score}/100", expanded=False):
            st.write(block.summary)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Points solides**")
                for x in block.strengths:
                    st.write(f"- {x}")
                st.markdown("**Quick wins**")
                for x in block.quick_wins:
                    st.write(f"- {x}")
            with c2:
                st.markdown("**Écarts visibles**")
                for x in block.gaps:
                    st.write(f"- {x}")
                st.markdown("**Actions recommandées**")
                for x in block.recommended_actions:
                    st.write(f"- {x}")
            st.markdown("**Risques**")
            for risk in block.risks:
                st.write(f"- **{risk.severity}** — {risk.title} : {risk.business_impact}")
