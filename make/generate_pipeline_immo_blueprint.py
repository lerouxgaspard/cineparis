#!/usr/bin/env python3
"""Génère le blueprint Make du scénario « Pipeline Immo - Lire email ».

Le scénario lit le label Gmail des dénonces immo et fait créer, par un agent IA,
une entrée dans la liste Attio « Dénonce Immo » (a804bc1b-…), sans doublon.

Toutes les configurations de modules ci-dessous ont été validées une par une
contre l'API Make (validate_module_configuration) — voir docs/pipeline-immo/.

    python3 make/generate_pipeline_immo_blueprint.py
"""

import json
from pathlib import Path

# --- Identifiants du workspace (relevés dans Attio / Make, ne pas deviner) ----

LIST_DENONCE_IMMO = "a804bc1b-8ea3-44ee-8b17-505f918413aa"  # liste « Dénonce Immo »
OBJECT_COMPANIES = "45b4d831-b5f5-41db-b3e9-239c683bbe63"   # objet « Companies »
ATTR_COMPANY_DOMAINS = "97d3d667-af5b-42f6-ad10-4fe4c48fe852"  # attribut unique « Domains »

# Statut (« Où en est le projet ? ») — attribut d'entrée `stage`
STATUT = {
    "A visiter": "982dc62d-506f-498a-9be0-c4aa77af759d",
    "Visité": "cac94b45-a838-4438-9380-e8f74e4f3811",
    "LOI envoyé": "91d611a2-a9ab-4f96-879b-c2eac300d71a",
    "Stand-by": "efcd0617-8e7f-4f55-bc4a-22d7d7172845",
    "Signé": "2f4d6976-73a9-4955-b9d2-1af33b2c3433",
}
# État (« Où en est le dossier ») — attribut d'entrée `status`
ETAT = {
    "Priorité": "4d5fa5b1-d5c8-44fc-bbde-284419d0d313",
    "En cours": "945d18ac-0aad-4ca9-8f31-12a9b1fce229",
    "Attente retour Propriétaire": "ae79f56a-afbf-4f20-9454-17096385378f",
    "Signé": "310a0159-093f-4646-a6a7-e14920bdbaed",
    "Stand-By": "7c56a631-be29-4621-9d42-91aef437f223",
}

# Connexions Make existantes de l'équipe Morning (16139)
CONN_GMAIL_GASPARD = 7498409       # My Gmail connection (gaspard.l@morning.fr)
CONN_ATTIO_OAUTH = 10415895        # Gaspard's Attio OAuth connection
CONN_AI_PROVIDER = 9767251         # Gaspard's Make's AI Provider connection

LABEL_PIPELINE_IMMO = "Label_3498769696537572611"  # label Gmail « Projet_pipeline_immo »

AGENT_ID = 83  # les entrées que l'agent remplit s'écrivent {{83.<champ>}}

# --- Instructions de l'agent -------------------------------------------------

SYSTEM_PROMPT = """\
Tu es l'assistant du pôle Immobilier de Morning. À chaque exécution tu reçois UN SEUL email, \
issu du label Gmail des dénonces immo : une offre de bureaux envoyée par un broker ou un \
propriétaire. Ton travail est d'enregistrer cette offre comme une entrée de la liste Attio \
« Dénonce Immo » — ou de ne rien faire si elle y figure déjà.

Tu tournes dans une automatisation : personne ne lit ta réponse en direct, personne ne peut \
répondre à une question. Ne demande JAMAIS de confirmation, ne propose jamais d'« actions \
recommandées », ne termine jamais par une question. Tu appelles les outils, puis tu rends un \
compte-rendu.

ÉTAPE 1 — EXTRAIRE (objet + corps de l'email)
- Nom du projet : adresse du bien, sous la forme « numéro rue - code postal ville »
  (ex. « 9 Cour des Petites Écuries - 75010 Paris »). C'est l'identifiant du projet.
- Surface : en m², nombre entier, sans unité.
- Entreprise qui porte l'offre (broker ou mandataire) et son domaine internet, déduit de
  l'adresse email de l'expéditeur d'origine (romain.rossel@spliit.fr -> spliit.fr).
- Propriétaire / bailleur : seulement s'il est nommé explicitement dans l'email.
- Commentaires : ce qu'un commercial doit savoir — étages, configuration, disponibilité,
  loyer, contact pour visite, conditions d'exclusivité.
N'invente rien : une information absente reste vide. Attention aux transferts internes :
un expéditeur @morning.fr n'est ni le broker ni le propriétaire, cherche l'email d'origine
dans le corps du message.

ÉTAPE 2 — VÉRIFIER LES DOUBLONS (obligatoire, avant toute création)
Appelle « Attio: Chercher un projet » avec un fragment court et discriminant de l'adresse
(ex. « Petites Écuries », pas l'adresse complète). Si une entrée renvoyée correspond au même
bien, ARRÊTE-TOI : ne crée rien, et indique dans le compte-rendu l'entrée qui existe déjà.

ÉTAPE 3 — RÉSOUDRE L'ENTREPRISE
Appelle « Attio: Trouver ou créer l'entreprise » avec le domaine trouvé à l'étape 1, et retiens
le record_id renvoyé (id.record_id). Si le domaine est une messagerie générique (gmail.com,
hotmail.com, outlook.com, yahoo.fr, free.fr, orange.fr...), n'appelle pas l'outil : sans
entreprise l'entrée ne peut pas être créée, arrête-toi et signale-le.

ÉTAPE 4 — CRÉER L'ENTRÉE
Appelle « Attio: Créer le deal » avec le record_id de l'étape 3 et les informations de
l'étape 1. Retiens l'entry_id renvoyé (id.entry_id).

ÉTAPE 5 — RATTACHER (seulement ce qui est connu)
- « Attio: Rattacher le broker » avec l'entry_id et le record_id de l'entreprise de l'étape 3.
- Propriétaire : uniquement s'il est nommé dans l'email. Résous d'abord son record_id avec
  « Attio: Trouver ou créer l'entreprise » (avec SON domaine), puis appelle
  « Attio: Rattacher le propriétaire ». Si tu n'as pas de domaine pour lui, n'appelle pas
  l'outil et note-le dans le compte-rendu.

RÈGLES
- Un email = une entrée au maximum. N'appelle jamais deux fois l'outil de création.
- Si un outil renvoie une erreur, ne réessaie qu'une fois, puis rends le compte-rendu en
  citant le message d'erreur.
- Ne t'occupe que de l'email reçu : ne va pas chercher d'autres emails.

COMPTE-RENDU (ta réponse finale, 7 lignes maximum, pas de question)
Action : créé | doublon | bloqué
Projet : ...
Entreprise : ... (record_id)
Surface : ...
Entry ID : ...
Propriétaire : ... | non nommé dans l'email
Manque : les champs que l'email ne permettait pas de remplir
"""

AGENT_INPUT = """\
De : {{94.fromName}} <{{94.fromEmail}}>
Date : {{94.internalDate}}
Objet : {{94.subject}}
Pièce(s) jointe(s) : {{94.hasAttachment}}

--- Corps de l'email ---
{{94.fullTextBody}}
"""

# --- Outils de l'agent -------------------------------------------------------

TOOL_SEARCH = {
    "name": "Attio: Chercher un projet",
    "description": (
        "Cherche dans la liste Attio « Dénonce Immo » les entrées dont le nom du projet "
        "contient le texte donné, pour éviter les doublons. Passe un fragment court et "
        "discriminant de l'adresse (ex. « Petites Écuries », « Falguière »), jamais "
        "l'adresse complète : la recherche est un « contient » strict, sensible à la "
        "ponctuation. Renvoie de 0 à 10 entrées existantes ; aucun résultat signifie que "
        "le projet n'est pas encore dans la liste."
    ),
    "flow": [
        {
            "id": 101,
            "module": "attio:searchEntries",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ATTIO_OAUTH},
            "mapper": {
                "list_id": LIST_DENONCE_IMMO,
                "queryBuilder": "simple",
                "filter": [
                    [
                        {
                            "a": "nom_du_projet",
                            "o": "text:$contains",
                            "b": f"{{{{{AGENT_ID}.recherche_nom_du_projet}}}}",
                        }
                    ]
                ],
                "limit": 10,
            },
            "metadata": {
                "designer": {"x": 900, "y": 300},
                "restore": {
                    "parameters": {
                        "__IMTCONN__": {
                            "label": "Gaspard's Attio OAuth connection (gaspard.l@morning.fr (Morning))",
                            "data": {"scoped": "true", "connection": "attio2"},
                        }
                    }
                },
            },
        }
    ],
}

TOOL_COMPANY = {
    "name": "Attio: Trouver ou créer l'entreprise",
    "description": (
        "Trouve la company Attio qui porte ce domaine internet, ou la crée si elle n'existe "
        "pas encore, et renvoie son record_id (champ id.record_id) — c'est ce record_id qu'il "
        "faut réutiliser pour créer l'entrée et pour les rattachements. Passe le domaine nu, "
        "sans « https:// » ni « www. » (ex. spliit.fr). N'appelle pas cet outil avec un domaine "
        "de messagerie générique (gmail.com, outlook.com, yahoo.fr...) : cela créerait une "
        "fausse entreprise."
    ),
    "flow": [
        {
            "id": 102,
            "module": "attio:assertACompany",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ATTIO_OAUTH},
            "mapper": {
                "matching_attribute": ATTR_COMPANY_DOMAINS,
                "[domain]domains": [f"{{{{{AGENT_ID}.domaine_entreprise}}}}"],
            },
            "metadata": {
                "designer": {"x": 900, "y": 500},
                "restore": {
                    "expect": {"matching_attribute": {"mode": "chose", "label": "Domains"}},
                    "parameters": {
                        "__IMTCONN__": {
                            "label": "Gaspard's Attio OAuth connection (gaspard.l@morning.fr (Morning))",
                            "data": {"scoped": "true", "connection": "attio2"},
                        }
                    },
                },
            },
        }
    ],
}

TOOL_CREATE = {
    "name": "Attio: Créer le deal",
    "description": (
        "Crée l'entrée du projet dans la liste Attio « Dénonce Immo », rattachée à la company "
        "dont tu passes le record_id (celui renvoyé par « Attio: Trouver ou créer "
        "l'entreprise »). À n'appeler qu'une seule fois, et seulement après avoir vérifié "
        "l'absence de doublon.\n"
        "Champs :\n"
        "- company_record_id (obligatoire) : record_id de la company qui porte l'offre.\n"
        "- nom_du_projet (obligatoire) : adresse du bien, « numéro rue - code postal ville ».\n"
        "- commentaires : le résumé utile au commercial (étages, dispo, loyer, contact visite).\n"
        "- surface : nombre entier de m², sans unité. Laisse vide si l'email ne le dit pas.\n"
        "- annee_du_projet : année de disponibilité si elle est mentionnée (ex. 2027).\n"
        "- statut : passe l'un de ces identifiants exactement — "
        f"{STATUT['A visiter']} (A visiter, valeur par défaut pour une nouvelle dénonce), "
        f"{STATUT['Visité']} (Visité), {STATUT['LOI envoyé']} (LOI envoyé), "
        f"{STATUT['Stand-by']} (Stand-by), {STATUT['Signé']} (Signé).\n"
        "- etat : passe l'un de ces identifiants exactement — "
        f"{ETAT['En cours']} (En cours, valeur par défaut), {ETAT['Priorité']} (Priorité), "
        f"{ETAT['Attente retour Propriétaire']} (Attente retour Propriétaire), "
        f"{ETAT['Stand-By']} (Stand-By), {ETAT['Signé']} (Signé).\n"
        "Renvoie id.entry_id : garde-le pour les rattachements."
    ),
    "flow": [
        {
            "id": 103,
            "module": "attio:createAnEntry",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ATTIO_OAUTH},
            "mapper": {
                "selectRecordId": "manually",
                "parent_object": OBJECT_COMPANIES,
                "id": LIST_DENONCE_IMMO,
                "parent_record_id": f"{{{{{AGENT_ID}.company_record_id}}}}",
                "[text]nom_du_projet": f"{{{{{AGENT_ID}.nom_du_projet}}}}",
                "[text]commentaires": f"{{{{{AGENT_ID}.commentaires}}}}",
                "[number]surface": f"{{{{{AGENT_ID}.surface}}}}",
                "[text]annee_du_p": f"{{{{{AGENT_ID}.annee_du_projet}}}}",
                "[status]stage": f"{{{{{AGENT_ID}.statut}}}}",
                "[status]status": f"{{{{{AGENT_ID}.etat}}}}",
            },
            "metadata": {
                "designer": {"x": 900, "y": 700},
                "restore": {
                    "expect": {
                        "selectRecordId": {"mode": "chose", "label": "Manually"},
                        "parent_object": {"mode": "chose", "label": "Company"},
                        "id": {"mode": "chose", "label": "Dénonce Immo"},
                    },
                    "parameters": {
                        "__IMTCONN__": {
                            "label": "Gaspard's Attio OAuth connection (gaspard.l@morning.fr (Morning))",
                            "data": {"scoped": "true", "connection": "attio2"},
                        }
                    },
                },
            },
        }
    ],
}


def _patch_entry_tool(module_id, name, description, attribute, agent_field, y):
    """Outil de rattachement d'une référence company sur l'entrée créée.

    Les attributs « Broker » et « Propriétaire » de la liste sont des références vers
    companies : le module « Create an Entry » de Make ne les expose pas, on passe donc
    par l'API Attio (PATCH d'une entrée existante).
    """
    body = json.dumps(
        {
            "data": {
                "entry_values": {
                    attribute: [
                        {
                            "target_object": "companies",
                            "target_record_id": f"{{{{{AGENT_ID}.{agent_field}}}}}",
                        }
                    ]
                }
            }
        },
        ensure_ascii=False,
        indent=2,
    )
    return {
        "name": name,
        "description": description,
        "flow": [
            {
                "id": module_id,
                "module": "attio:makeAnApiCall",
                "version": 2,
                "parameters": {"__IMTCONN__": CONN_ATTIO_OAUTH},
                "mapper": {
                    "url": f"/v2/lists/{LIST_DENONCE_IMMO}/entries/{{{{{AGENT_ID}.entry_id}}}}",
                    "method": "PATCH",
                    "headers": [{"key": "Content-Type", "value": "application/json"}],
                    "body": body,
                },
                "metadata": {
                    "designer": {"x": 900, "y": y},
                    "restore": {
                        "expect": {"method": {"mode": "chose", "label": "PATCH"}},
                        "parameters": {
                            "__IMTCONN__": {
                                "label": "Gaspard's Attio OAuth connection (gaspard.l@morning.fr (Morning))",
                                "data": {"scoped": "true", "connection": "attio2"},
                            }
                        },
                    },
                },
            }
        ],
    }


TOOL_LINK_BROKER = _patch_entry_tool(
    104,
    "Attio: Rattacher le broker",
    "Renseigne le champ « Broker » de l'entrée créée. Passe entry_id (renvoyé par "
    "« Attio: Créer le deal ») et broker_record_id (le record_id de la company du broker). "
    "N'appelle cet outil qu'après la création de l'entrée.",
    "broker",
    "broker_record_id",
    900,
)

TOOL_LINK_OWNER = _patch_entry_tool(
    105,
    "Attio: Rattacher le propriétaire",
    "Renseigne le champ « Propriétaire » de l'entrée créée. Passe entry_id et "
    "proprietaire_record_id (le record_id de la company du propriétaire, obtenu avec "
    "« Attio: Trouver ou créer l'entreprise »). N'appelle cet outil que si le propriétaire "
    "est explicitement nommé dans l'email.",
    "proprietaire",
    "proprietaire_record_id",
    1100,
)

# --- Flux principal ----------------------------------------------------------

TRIGGER = {
    "id": 94,
    "module": "google-email:triggerWatchNewEmails",
    "version": 4,
    "parameters": {
        "__IMTCONN__": CONN_GMAIL_GASPARD,
        "filterType": "simpleSearch",
        "format": "full",
        "folder": "INBOX",
        "labelIds": LABEL_PIPELINE_IMMO,
        "criteria": "all",
        "markSeen": False,
        "limit": 5,
        "from": "",
        "subject": "",
        "includeWords": "",
        "excludeWords": "",
        "size": {"criteria": "larger", "amount": None, "unit": "M"},
        "hasAttachment": False,
    },
    "mapper": {},
    "metadata": {
        "designer": {"x": 0, "y": 0},
        "restore": {
            "parameters": {
                "__IMTCONN__": {
                    "label": "My Gmail connection (gaspard.l@morning.fr)",
                    "data": {"scoped": "true", "connection": "google-email"},
                },
                "filterType": {"label": "Simple filter"},
                "format": {"label": "Full content"},
                "folder": {"label": "Inbox"},
                "labelIds": {"label": "Projet_pipeline_immo"},
                "criteria": {"label": "All messages"},
                "size": {"nested": {"criteria": {"label": "Greater than"}, "unit": {"label": "MB (megabytes)"}}},
            }
        },
    },
}

AGENT = {
    "id": AGENT_ID,
    "module": "ai-local-agent:RunLocalAIAgent",
    "version": 0,
    "parameters": {"makeConnectionId": CONN_AI_PROVIDER},
    "mapper": {
        "files": [],
        "message": AGENT_INPUT,
        "threadId": "",
        "outputType": "text",
        "tokenLimit": "100",
        "modelConfig": {
            "timeout": "",
            "recursionLimit": 25,
            "iterationsFromHistoryCount": 10,
        },
        # À changer dans l'interface Make après import : choisir le grand modèle.
        # La liste des modèles vient d'une RPC liée à la connexion, on ne l'écrit pas ici.
        "defaultModel": "medium",
        "systemPrompt": SYSTEM_PROMPT,
        "promptCaching": "none",
        "fallbackEnabled": False,
    },
    "tools": [
        TOOL_SEARCH,
        TOOL_COMPANY,
        TOOL_CREATE,
        TOOL_LINK_BROKER,
        TOOL_LINK_OWNER,
    ],
    "metadata": {
        "designer": {"x": 450, "y": 0},
        "restore": {
            "expect": {"files": {"mode": "chose"}, "outputType": {"label": "Text"}},
            "parameters": {
                "makeConnectionId": {
                    "label": "Gaspard's Make's AI Provider connection",
                    "data": {"scoped": "true", "connection": "ai-provider"},
                }
            },
        },
    },
}

BLUEPRINT = {
    "name": "[DEV] Pipeline Immo - Lire email - Gaspard",
    "flow": [TRIGGER, AGENT],
    "metadata": {
        "instant": False,
        "version": 1,
        "scenario": {
            "roundtrips": 1,
            "maxErrors": 3,
            "autoCommit": True,
            "autoCommitTriggerLast": True,
            "sequential": True,
            "slots": None,
            "confidential": False,
            "dataloss": False,
            "dlq": False,
            "freshVariables": False,
        },
        "designer": {"orphans": []},
    },
}


def main():
    out = Path(__file__).with_name("pipeline-immo-lire-email.blueprint.json")
    out.write_text(json.dumps(BLUEPRINT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"écrit {out} ({out.stat().st_size} octets)")


if __name__ == "__main__":
    main()
