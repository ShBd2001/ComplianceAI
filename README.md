# ComplianceAI 

Application Streamlit de diagnostic conformité / cyber / RSE avec questionnaire adaptatif.

## Ce que fait le projet

- le profil entreprise pilote le cadrage de l'analyse
- le questionnaire est généré selon le secteur, la taille et le contexte
- l'interface reste orientée métier
- le rapport PDF reprend la synthèse, les priorités, la roadmap et l'annexe questions/réponses

## Structure

- `app.py` : interface Streamlit
- `backend.py` : appels LLM et orchestration backend
- `prompts.py` : prompts backend
- `schemas.py` : schémas JSON stricts
- `fallback_data.py` : secours local si le backend n'est pas disponible
- `report.py` : génération du PDF

## Lancer le projet

```bash
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## Remarques

- l'interface ne demande aucune saisie technique
- la configuration serveur est lue côté backend
- le projet peut retomber sur un mode de secours local si le backend n'est pas joignable
