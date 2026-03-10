from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from schemas import ContextPack, DomainOutput, DomainRisk, OrchestratorOutput, QuestionItem, QuestionnairePack

ANSWER_VALUE = {"Oui": 1.0, "Partiellement": 0.55, "Non": 0.0}
DOMAIN_ORDER = ["CYBER", "RGPD", "RSE"]


SECTOR_EXPOSURES = {
    "Santé": [
        "données sensibles patients ou RH",
        "continuité d'activité critique",
        "gestion fine des habilitations",
        "prestataires et hébergeurs à surveiller",
    ],
    "Finance": [
        "forte exigence de traçabilité",
        "risque élevé en cas d'incident de sécurité",
        "sous-traitance et outils SaaS à contrôler",
        "pression client sur la gouvernance",
    ],
    "E-commerce": [
        "paiement et fraude",
        "cookies et parcours marketing",
        "données clients volumineuses",
        "dépendance à la disponibilité du site",
    ],
    "Industrie": [
        "continuité de production",
        "accès tiers et maintenance",
        "systèmes hétérogènes",
        "chaîne fournisseurs à encadrer",
    ],
    "Services": [
        "dépendance au cloud et aux postes de travail",
        "contrats et confidentialité client",
        "télétravail et accès distants",
        "preuve de maturité demandée par les prospects",
    ],
    "Autre": [
        "pilotage encore peu formalisé",
        "outils multiples et visibilité partielle",
        "dépendance aux prestataires",
        "besoin de priorisation rapide",
    ],
}


def _profile_summary(profile: Dict) -> str:
    return (
        f"{profile.get('name', 'Entreprise')} évolue dans le secteur {profile.get('sector', 'Autre')}, "
        f"avec environ {profile.get('employees', 0)} collaborateurs, un modèle {profile.get('business_model', 'B2B')} "
        f"et un niveau de sensibilité des données jugé {profile.get('data_sensitivity', 'moyen')}."
    )


def build_fallback_context(profile: Dict) -> ContextPack:
    sector = profile.get("sector", "Autre")
    size = int(profile.get("employees", 0) or 0)
    sensitivity = profile.get("data_sensitivity", "moyen")
    remote = profile.get("remote_work", "hybride")
    customers = profile.get("customer_type", "entreprises")

    exposures = list(SECTOR_EXPOSURES.get(sector, SECTOR_EXPOSURES["Autre"]))
    if sensitivity in {"élevé", "très élevé"}:
        exposures.insert(0, "traitement de données à forte sensibilité")
    if remote in {"hybride", "majoritairement à distance"}:
        exposures.append("surface d'attaque élargie par le travail à distance")
    if customers == "grand public":
        exposures.append("forte exposition sur transparence client et réputation")

    regulatory = ["sécurité opérationnelle", "documentation et preuves", "gestion des prestataires"]
    if sector in {"Santé", "Finance"}:
        regulatory.extend(["contrôles renforcés", "gestion des accès", "journalisation et traçabilité"])
    if sector == "E-commerce":
        regulatory.extend(["cookies et consentement", "parcours client", "gestion des incidents visibles côté client"])

    angles = [
        "questionner d'abord les contrôles réellement visibles",
        "privilégier les quick wins sous 90 jours",
        "lier chaque réponse à un impact métier simple",
    ]
    if size < 50:
        angles.append("rester compatible avec une petite équipe et un budget limité")
    if size >= 250:
        angles.append("tester aussi la gouvernance et la diffusion des pratiques")

    tone = "sobre, dirigeant, orienté arbitrage" if customers == "entreprises" else "clair, pédagogique, orienté confiance client"
    return ContextPack(
        profile_summary=_profile_summary(profile),
        executive_focus="prioriser ce qui réduit vite le risque sans alourdir inutilement l'organisation",
        key_exposures=exposures[:8],
        regulatory_focus=regulatory[:8],
        questionnaire_angles=angles[:8],
        reporting_tone=tone,
    )


COMMON_QUESTIONS = {
    "CYBER": [
        ("CY_BASE_1", "Les comptes sensibles sont-ils protégés par MFA ?", "Accès, messagerie, VPN, outils d'administration.", "Empêche les compromissions simples.", 16, True),
        ("CY_BASE_2", "Les sauvegardes sont-elles testées et restaurables ?", "Pas seulement présentes, mais réellement testées.", "Conditionne la reprise après incident.", 16, True),
        ("CY_BASE_3", "Les postes et serveurs sont-ils patchés régulièrement ?", "Process simple, fréquence, preuves minimales.", "Réduit les vulnérabilités exploitables.", 12, False),
        ("CY_BASE_4", "Les accès sont-ils revus selon le moindre privilège ?", "Départs, arrivées, comptes partagés, droits admin.", "Limite la propagation d'une attaque.", 12, True),
    ],
    "RGPD": [
        ("RG_BASE_1", "Les traitements de données sont-ils cartographiés ?", "Registre ou document équivalent tenu à jour.", "Donne une base de pilotage conformité.", 15, True),
        ("RG_BASE_2", "Les durées de conservation et suppressions sont-elles définies ?", "Données clients, RH, prospects, support.", "Réduit l'exposition inutile.", 13, True),
        ("RG_BASE_3", "Les sous-traitants clés sont-ils encadrés contractuellement ?", "Clauses, DPA, responsabilités, localisation.", "Sécurise la chaîne de traitement.", 12, True),
        ("RG_BASE_4", "Le traitement des demandes d'accès ou suppression est-il cadré ?", "Qui reçoit, qui traite, sous quel délai.", "Évite les retards et erreurs.", 10, False),
    ],
    "RSE": [
        ("RSE_BASE_1", "Une feuille de route RSE est-elle formalisée ?", "Même simple, avec objectifs et porteur identifié.", "Évite une démarche purement déclarative.", 14, False),
        ("RSE_BASE_2", "Des indicateurs simples sont-ils suivis ?", "Ex: énergie, déchets, absentéisme, achats responsables.", "Rend la progression crédible.", 12, False),
        ("RSE_BASE_3", "Les fournisseurs critiques sont-ils évalués sous un angle RSE ?", "Charte, critères, clauses ou revue simple.", "Réduit l'exposition chaîne de valeur.", 12, False),
        ("RSE_BASE_4", "Des actions RH/éthique concrètes sont-elles en place ?", "Inclusion, alerte, formation, règles de conduite.", "Renforce la crédibilité interne et externe.", 10, False),
    ],
}

SECTOR_QUESTIONS = {
    "Santé": {
        "CYBER": [
            ("CY_HEALTH_1", "Les accès aux dossiers sensibles sont-ils tracés et revus ?", "Traçabilité et revue périodique des habilitations.", "Réduit les usages non autorisés.", 15, True),
            ("CY_HEALTH_2", "La continuité d'activité est-elle préparée pour une indisponibilité SI ?", "Procédures dégradées, restauration, dépendances critiques.", "Limite l'impact opérationnel.", 14, True),
        ],
        "RGPD": [
            ("RG_HEALTH_1", "Les données sensibles font-elles l'objet de mesures renforcées ?", "Minimisation, accès, conservation, chiffrement, journalisation.", "Réduit l'exposition la plus critique.", 16, True),
            ("RG_HEALTH_2", "Les habilitations par métier sont-elles documentées ?", "Profils d'accès, exceptions, revues.", "Réduit les écarts d'accès.", 12, True),
        ],
        "RSE": [
            ("RSE_HEALTH_1", "Les enjeux qualité de vie au travail sont-ils suivis ?", "Charge, prévention, organisation, astreintes.", "Agit sur la durabilité sociale.", 11, False),
        ],
    },
    "Finance": {
        "CYBER": [
            ("CY_FIN_1", "Les actions sensibles sont-elles journalisées et revues ?", "Connexion, validation, changements critiques.", "Renforce la traçabilité.", 15, True),
            ("CY_FIN_2", "Les accès tiers et prestataires sont-ils maîtrisés ?", "Comptes dédiés, expiration, supervision.", "Réduit le risque indirect.", 13, True),
        ],
        "RGPD": [
            ("RG_FIN_1", "Les bases légales et usages des données sont-ils documentés ?", "Prospection, KYC, relation client, RH.", "Sécurise la licéité des traitements.", 14, True),
            ("RG_FIN_2", "Les transferts et partages de données sont-ils encadrés ?", "Prestataires, partenaires, outils externes.", "Réduit le risque de diffusion non maîtrisée.", 12, True),
        ],
        "RSE": [
            ("RSE_FIN_1", "Les critères éthiques et de gouvernance sont-ils formalisés ?", "Code de conduite, prévention des conflits, alerte.", "Renforce la confiance client et investisseur.", 12, False),
        ],
    },
    "E-commerce": {
        "CYBER": [
            ("CY_ECOM_1", "Le site et les parcours de paiement sont-ils surveillés activement ?", "Alertes, journaux, disponibilité, dépendances critiques.", "Protège le revenu direct.", 15, True),
            ("CY_ECOM_2", "Une procédure existe-t-elle en cas de fraude ou compromission de compte ?", "Détection, gel, communication, support.", "Réduit la perte client et réputation.", 13, True),
        ],
        "RGPD": [
            ("RG_ECOM_1", "Le consentement cookies et marketing est-il maîtrisé ?", "Bannières, preuves, retrait, finalités.", "Sujet visible côté client.", 14, True),
            ("RG_ECOM_2", "Les données clients sont-elles limitées à l'utile ?", "Prospection, paniers, SAV, fidélité.", "Réduit l'accumulation inutile.", 11, False),
        ],
        "RSE": [
            ("RSE_ECOM_1", "Les emballages, retours et transport font-ils l'objet d'un suivi ?", "Suivi simple, objectifs, fournisseurs.", "Impact visible pour le client.", 11, False),
        ],
    },
    "Industrie": {
        "CYBER": [
            ("CY_IND_1", "Les accès de maintenance et prestataires sont-ils encadrés ?", "Accès temporaires, supervision, segmentation.", "Point d'entrée fréquent en environnement industriel.", 15, True),
            ("CY_IND_2", "Les actifs critiques de production sont-ils inventoriés ?", "Machines, serveurs, logiciels, dépendances.", "Permet de cibler les protections.", 13, True),
        ],
        "RGPD": [
            ("RG_IND_1", "Les données RH, visiteurs et vidéosurveillance sont-elles cadrées ?", "Finalités, conservation, information.", "Réduit un risque souvent sous-estimé.", 12, False),
        ],
        "RSE": [
            ("RSE_IND_1", "L'énergie, les déchets et incidents environnementaux sont-ils suivis ?", "Mesure, objectifs, revue simple.", "Impact direct sur performance et image.", 14, False),
            ("RSE_IND_2", "Les fournisseurs critiques sont-ils évalués sur leurs pratiques ?", "Sécurité, environnement, continuité, éthique.", "Réduit le risque d'approvisionnement.", 11, False),
        ],
    },
    "Services": {
        "CYBER": [
            ("CY_SERV_1", "Les accès distants et outils cloud sont-ils centralisés ?", "SSO, MFA, comptes partagés, offboarding.", "Point critique pour une PME de services.", 14, True),
            ("CY_SERV_2", "Les collaborateurs sont-ils sensibilisés au phishing ?", "Formation courte, tests ou rappels réguliers.", "Réduit le risque humain.", 11, False),
        ],
        "RGPD": [
            ("RG_SERV_1", "Les engagements de confidentialité client sont-ils maîtrisés ?", "Contrats, accès, partage interne, support.", "Fort enjeu commercial.", 13, True),
            ("RG_SERV_2", "Les données prospects et CRM sont-elles gouvernées ?", "Conservation, base légale, accès, export.", "Sujet fréquent en croissance commerciale.", 11, False),
        ],
        "RSE": [
            ("RSE_SERV_1", "Les engagements sociaux et qualité de vie au travail sont-ils suivis ?", "Onboarding, charge, management, feedback.", "Améliore rétention et image employeur.", 11, False),
        ],
    },
}


def build_fallback_questionnaire(profile: Dict, context: ContextPack) -> QuestionnairePack:
    sector = profile.get("sector", "Autre")
    questions: List[QuestionItem] = []
    domain_counts = {"CYBER": 0, "RGPD": 0, "RSE": 0}

    for domain in DOMAIN_ORDER:
        for row in COMMON_QUESTIONS[domain]:
            questions.append(QuestionItem(id=row[0], domain=domain, label=row[1], help_text=row[2], rationale=row[3], weight=row[4], critical=row[5]))
            domain_counts[domain] += 1

    sector_rows = SECTOR_QUESTIONS.get(sector, SECTOR_QUESTIONS.get("Services", {}))
    for domain in DOMAIN_ORDER:
        for row in sector_rows.get(domain, []):
            questions.append(QuestionItem(id=row[0], domain=domain, label=row[1], help_text=row[2], rationale=row[3], weight=row[4], critical=row[5]))
            domain_counts[domain] += 1

    if profile.get("remote_work") in {"hybride", "majoritairement à distance"} and domain_counts["CYBER"] < 6:
        questions.append(
            QuestionItem(
                id="CY_REMOTE_1",
                domain="CYBER",
                label="Les appareils mobiles et postes distants sont-ils gérés de façon homogène ?",
                help_text="Configuration, mises à jour, verrouillage, départs, stockage local.",
                rationale="Le travail à distance augmente l'exposition opérationnelle.",
                weight=12,
                critical=True,
            )
        )
        domain_counts["CYBER"] += 1

    if profile.get("data_sensitivity") in {"élevé", "très élevé"} and domain_counts["RGPD"] < 6:
        questions.append(
            QuestionItem(
                id="RG_SENS_1",
                domain="RGPD",
                label="Les données sensibles ou stratégiques font-elles l'objet de contrôles renforcés ?",
                help_text="Accès, conservation, export, journalisation, chiffrement, besoin d'en connaître.",
                rationale="Les données sensibles concentrent l'essentiel du risque.",
                weight=15,
                critical=True,
            )
        )
        domain_counts["RGPD"] += 1

    if profile.get("supplier_dependency") == "forte" and domain_counts["RSE"] < 6:
        questions.append(
            QuestionItem(
                id="RSE_SUP_1",
                domain="RSE",
                label="Les fournisseurs stratégiques sont-ils évalués au-delà du prix ?",
                help_text="Délais, éthique, environnement, continuité, clauses, alternatives.",
                rationale="La dépendance fournisseur pèse sur la résilience globale.",
                weight=12,
                critical=False,
            )
        )
        domain_counts["RSE"] += 1

    intro = (
        f"Diagnostic ajusté pour une entreprise du secteur {profile.get('sector', 'Autre')} : "
        f"les questions mettent l'accent sur {', '.join(context.key_exposures[:3])}."
    )
    return QuestionnairePack(intro=intro, questions=questions)


def questions_by_domain(questions: Iterable[QuestionItem], domain: str) -> List[QuestionItem]:
    return [q for q in questions if q.domain == domain]


def compute_scores(questions: Iterable[QuestionItem], answers: Dict[str, str]) -> Dict[str, int]:
    totals = defaultdict(float)
    weights = defaultdict(float)
    for q in questions:
        weights[q.domain] += q.weight
        totals[q.domain] += q.weight * ANSWER_VALUE.get(answers.get(q.id, "Non"), 0.0)
    out = {}
    for domain in DOMAIN_ORDER:
        out[domain] = int(round((totals[domain] / weights[domain]) * 100)) if weights[domain] else 0
    out["GLOBAL"] = int(round(0.4 * out["CYBER"] + 0.35 * out["RGPD"] + 0.25 * out["RSE"]))
    return out


def _severity(answer: str, critical: bool) -> str:
    if answer == "Non" and critical:
        return "CRITIQUE"
    if answer == "Non":
        return "MOYEN"
    if answer == "Partiellement" and critical:
        return "MOYEN"
    return "FAIBLE"


def _risk_level(global_score: int, critical_count: int) -> str:
    if critical_count >= 3 or global_score < 55:
        return "élevé"
    if critical_count >= 1 or global_score < 75:
        return "modéré"
    return "faible"


def estimate_financial_risk(profile: Dict, level: str) -> tuple[int, int]:
    employees = int(profile.get("employees", 0) or 0)
    revenue = int(profile.get("annual_revenue", 0) or 0)
    base = max(8000, int(employees * 350 + revenue * 0.004))
    if level == "élevé":
        return base * 2, base * 6
    if level == "modéré":
        return base, base * 3
    return max(3000, base // 2), int(base * 1.5)


ACTION_LIBRARY = {
    "CYBER": {
        "CY_BASE_1": "Activer la MFA sur messagerie, VPN et comptes sensibles.",
        "CY_BASE_2": "Formaliser les sauvegardes et tester une restauration complète.",
        "CY_BASE_3": "Mettre en place un rythme de patching mensuel documenté.",
        "CY_BASE_4": "Revoir les droits et supprimer les comptes ou privilèges inutiles.",
        "CY_REMOTE_1": "Uniformiser la gestion des postes distants et mobiles.",
        "CY_SERV_1": "Centraliser les accès cloud avec SSO ou gouvernance équivalente.",
        "CY_SERV_2": "Lancer une sensibilisation phishing trimestrielle.",
        "CY_ECOM_1": "Mettre une supervision sur disponibilité, erreurs et paiement.",
        "CY_ECOM_2": "Écrire une procédure fraude/compromission de compte.",
        "CY_IND_1": "Encadrer les accès de maintenance et prestataires tiers.",
        "CY_IND_2": "Inventorier les actifs critiques de production.",
        "CY_HEALTH_1": "Revoir les habilitations et la traçabilité des accès sensibles.",
        "CY_HEALTH_2": "Préparer un mode dégradé en cas d'indisponibilité SI.",
        "CY_FIN_1": "Renforcer la journalisation et les revues d'opérations sensibles.",
        "CY_FIN_2": "Sécuriser les accès et durées d'autorisation des tiers.",
    },
    "RGPD": {
        "RG_BASE_1": "Créer ou remettre à jour la cartographie des traitements.",
        "RG_BASE_2": "Définir les durées de conservation et la purge associée.",
        "RG_BASE_3": "Mettre à jour les clauses et accords avec les sous-traitants clés.",
        "RG_BASE_4": "Formaliser un processus de gestion des droits des personnes.",
        "RG_SENS_1": "Encadrer spécifiquement les données sensibles ou stratégiques.",
        "RG_SERV_1": "Sécuriser la confidentialité client de bout en bout.",
        "RG_SERV_2": "Nettoyer et gouverner les données CRM et prospects.",
        "RG_ECOM_1": "Remettre à plat le recueil et la preuve du consentement.",
        "RG_ECOM_2": "Réduire les données clients stockées au strict utile.",
        "RG_IND_1": "Revoir les traitements RH, visiteurs et vidéosurveillance.",
        "RG_HEALTH_1": "Appliquer des mesures renforcées sur les données sensibles.",
        "RG_HEALTH_2": "Documenter les habilitations par métier.",
        "RG_FIN_1": "Documenter bases légales et usages des données.",
        "RG_FIN_2": "Encadrer strictement les partages et transferts de données.",
    },
    "RSE": {
        "RSE_BASE_1": "Formaliser une feuille de route RSE courte et pilotable.",
        "RSE_BASE_2": "Choisir 3 à 5 KPI RSE suivis chaque mois.",
        "RSE_BASE_3": "Évaluer les fournisseurs critiques avec un filtre RSE minimal.",
        "RSE_BASE_4": "Structurer des actions RH/éthique visibles et mesurables.",
        "RSE_SUP_1": "Ajouter des critères de résilience et d'éthique dans les achats.",
        "RSE_SERV_1": "Suivre un petit socle d'indicateurs sociaux et QVT.",
        "RSE_ECOM_1": "Mesurer emballages, retours et transport pour prioriser les gains.",
        "RSE_IND_1": "Structurer le suivi énergie, déchets et incidents environnementaux.",
        "RSE_IND_2": "Encadrer les fournisseurs critiques avec une revue régulière.",
        "RSE_HEALTH_1": "Suivre les signaux RH et organisationnels à risque.",
        "RSE_FIN_1": "Formaliser gouvernance éthique et mécanismes d'alerte.",
    },
}


def fallback_domain_analysis(domain: str, profile: Dict, questions: List[QuestionItem], answers: Dict[str, str]) -> DomainOutput:
    domain_questions = questions_by_domain(questions, domain)
    score = compute_scores(domain_questions, answers)[domain]
    strengths: List[str] = []
    gaps: List[str] = []
    risks: List[DomainRisk] = []
    quick_wins: List[str] = []
    recommended_actions: List[str] = []

    for q in domain_questions:
        answer = answers.get(q.id, "Non")
        if answer == "Oui" and len(strengths) < 4:
            strengths.append(q.label)
        if answer in {"Non", "Partiellement"}:
            if len(gaps) < 6:
                gaps.append(q.label)
            sev = _severity(answer, q.critical)
            if len(risks) < 6:
                risks.append(
                    DomainRisk(
                        title=q.label,
                        severity=sev,
                        reason=f"Réponse '{answer.lower()}' sur un contrôle clé du domaine.",
                        business_impact="Exposition accrue, manque de preuve, ou difficulté de réaction en cas d'incident.",
                    )
                )
            action = ACTION_LIBRARY.get(domain, {}).get(q.id)
            if action and action not in recommended_actions:
                recommended_actions.append(action)
                if answer == "Non" and len(quick_wins) < 4:
                    quick_wins.append(action)

    confidence = "haute" if len(domain_questions) >= 5 else "moyenne"
    if score < 50:
        summary = f"Le niveau de maturité {domain} apparaît insuffisant au regard du profil déclaré. Les réponses montrent plusieurs fondamentaux absents ou incomplets."
    elif score < 75:
        summary = f"Le domaine {domain} est partiellement structuré mais encore fragile sur plusieurs points visibles. Une priorisation à court terme est nécessaire."
    else:
        summary = f"Le domaine {domain} est plutôt bien couvert dans les réponses, avec quelques ajustements encore utiles pour consolider la preuve et la régularité."

    if not strengths:
        strengths.append("Peu d'éléments pleinement stabilisés ressortent du diagnostic.")
    if not recommended_actions:
        recommended_actions.append("Maintenir les pratiques existantes et documenter davantage la preuve de maîtrise.")
    if not quick_wins:
        quick_wins = recommended_actions[:3]

    return DomainOutput(
        domain=domain,
        score=score,
        summary=summary,
        strengths=strengths[:4],
        gaps=gaps[:6],
        risks=risks[:6],
        quick_wins=quick_wins[:4],
        recommended_actions=recommended_actions[:6],
        confidence=confidence,
    )


def fallback_orchestrator(profile: Dict, analyses: List[DomainOutput]) -> OrchestratorOutput:
    scores = {x.domain: x.score for x in analyses}
    global_score = int(round(0.4 * scores.get("CYBER", 0) + 0.35 * scores.get("RGPD", 0) + 0.25 * scores.get("RSE", 0)))
    critical_count = sum(1 for a in analyses for r in a.risks if r.severity == "CRITIQUE")
    level = _risk_level(global_score, critical_count)
    low, high = estimate_financial_risk(profile, level)

    priorities: List[str] = []
    for analysis in sorted(analyses, key=lambda a: a.score):
        for action in analysis.recommended_actions:
            if action not in priorities:
                priorities.append(action)

    roadmap_30 = priorities[:3]
    roadmap_60 = priorities[3:6]
    roadmap_90 = priorities[6:9]
    watchouts = []
    if scores.get("CYBER", 0) < 60:
        watchouts.append("Risque d'interruption d'activité ou de compromission encore trop élevé.")
    if scores.get("RGPD", 0) < 60:
        watchouts.append("Documentation et encadrement des traitements insuffisants pour répondre sereinement à une demande ou un incident.")
    if scores.get("RSE", 0) < 60:
        watchouts.append("La démarche RSE reste peu structurée et peut manquer de crédibilité face à des clients ou partenaires exigeants.")
    if not watchouts:
        watchouts.append("Le principal enjeu est maintenant la régularité et la preuve des pratiques en place.")

    executive_summary = (
        f"Le diagnostic situe l'entreprise à {global_score}/100. Les priorités portent d'abord sur les contrôles visibles qui réduisent rapidement le risque, "
        f"puis sur la documentation et le pilotage pour stabiliser la démarche."
    )
    business_takeaway = (
        "Le sujet n'est pas seulement réglementaire : il touche la continuité d'activité, la confiance client et la capacité à répondre à des demandes de preuve."
    )
    return OrchestratorOutput(
        executive_summary=executive_summary,
        business_takeaway=business_takeaway,
        global_score=global_score,
        risk_level=level,
        top_priorities=priorities[:8],
        roadmap_30=roadmap_30,
        roadmap_60=roadmap_60,
        roadmap_90=roadmap_90,
        watchouts=watchouts[:5],
        financial_range_low=low,
        financial_range_high=high,
    )
