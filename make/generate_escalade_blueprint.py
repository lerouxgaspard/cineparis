#!/usr/bin/env python3
"""Génère le blueprint Make « [PRD] [Attio] Escalade 5 min - À la journée ».

Scénario planifié : le module Sleep de Make est plafonné à 300 s, un délai de
15 minutes en ligne est donc impossible — et bloquer un run webhook 15 minutes
empilerait les exécutions. L'escalade est un scénario séparé.

Forme retenue : un DIGEST. Mesuré le 08/09 sur 4 h de données réelles, six leads
étaient restés au stage Contact Entrant — la règle des 5 minutes n'est presque
jamais tenue. Un DM par lead aurait donné ~20 notifications par jour à une seule
personne, qui les aurait coupées en une journée. Un seul message par passage,
listant les leads en souffrance, reste lisible.

PRÉREQUIS : la checkbox `escalade_envoyee` sur l'objet deals_daily.
Régénérer avec :  python3 make/generate_escalade_blueprint.py
"""
import json
import pathlib

CONN_ATTIO = 3292919
CONN_AIRTABLE = 2426866
CONN_SLACK = 53760

ATTIO_OBJECT = "deals_daily"
DESTINATAIRE = "jules.b@morning.fr"
STAGE_ENTREE = "Contact Entrant"
DELAI_MINUTES = 15
FENETRE_HEURES = 4        # ne jamais escalader un lead plus vieux que ça

AT_BASE = "app1ZLIN13lGG0cPE"
AT_TABLE = "tbl362A2eveuwpuBE"          # Equipe_Daily

QUERY_BODY = json.dumps({
    "filter": {
        "$and": [
            {"stage": {"$eq": STAGE_ENTREE}},
            # $not plutôt que $eq false : l'attribut a été créé après coup, il est
            # absent (null) de tout l'historique, et null != false.
            {"$not": {"escalade_envoyee": {"$eq": True}}},
            {"created_at": {
                "$lt": "{{formatDate(addMinutes(now; -%d); \"YYYY-MM-DDTHH:mm:ss[Z]\"; \"UTC\")}}"
                % DELAI_MINUTES}},
            # Borne basse indispensable : sans elle le premier passage remonterait
            # tout l'historique resté à Contact Entrant (50+ deals au 08/09).
            {"created_at": {
                "$gt": "{{formatDate(addHours(now; -%d); \"YYYY-MM-DDTHH:mm:ss[Z]\"; \"UTC\")}}"
                % FENETRE_HEURES}},
        ]
    },
    "sorts": [{"direction": "asc", "attribute": "created_at", "field": "value"}],
    "limit": 50,
}, ensure_ascii=False)

# Une ligne de digest par lead. Le propriétaire est résolu en nom via Equipe_Daily :
# l'API Attio ne renvoie qu'un UUID, illisible dans Slack.
LIGNE = (
    "• *{{replace(ifempty(4.values.name[].value; \"sans nom\"); \"/[\\r\\n\\t]+/g\"; \" \")}}* — "
    "{{ifempty(get(first(4.values.value); \"currency_value\"); 0)}} EUR — "
    "{{ifempty(first(map(3.array; \"name\"; \"attio_user_id\"; "
    "first(map(4.values.owner; \"referenced_actor_id\")))); \"non attribué\")}} — "
    "créé à {{formatDate(4.values.created_at[].value; \"HH:mm\"; \"Europe/Paris\")}} — "
    "<https://app.attio.com/morning-prod/custom/deals_daily/record/{{4.id.record_id}}|ouvrir>"
)

DIGEST_BLOCKS = json.dumps({"blocks": [
    {"type": "header", "text": {"type": "plain_text",
                                "text": ":warning: Leads non traités depuis 15 min",
                                "emoji": True}},
    {"type": "section", "text": {"type": "mrkdwn",
                                 "text": "{{join(map(6.array; \"ligne\"); \"\\n\")}}"}},
    {"type": "context", "elements": [
        {"type": "mrkdwn",
         "text": "Toujours au stage *Contact Entrant* — la règle des 5 minutes n'a pas été tenue."}]},
]}, ensure_ascii=False, indent=1)


def build():
    flow = [
        # 1 — Les leads en souffrance
        {
            "id": 1,
            "module": "attio:makeAnApiCall",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ATTIO},
            "mapper": {
                "url": f"/v2/objects/{ATTIO_OBJECT}/records/query",
                "method": "POST",
                "headers": [{"key": "Content-Type", "value": "application/json"}],
                "body": QUERY_BODY,
            },
            "metadata": {"designer": {"x": 0, "y": 0,
                                      "name": "Attio - Leads non traités"}},
        },
        # 2/3 — Le trombinoscope, pour traduire les UUID en noms
        {
            "id": 2,
            "module": "airtable:ActionSearchRecords",
            "version": 3,
            "parameters": {"__IMTCONN__": CONN_AIRTABLE},
            "mapper": {
                "base": AT_BASE,
                "table": AT_TABLE,
                "formula": "",
                "maxRecords": 50,
                "useColumnId": False,
            },
            "metadata": {"designer": {"x": 300, "y": 0, "name": "Airtable - Équipe"}},
        },
        {
            "id": 3,
            "module": "builtin:BasicAggregator",
            "version": 1,
            "parameters": {"feeder": 2},
            "mapper": {"name": "{{2.name}}", "attio_user_id": "{{2.attio_user_id}}"},
            "metadata": {"designer": {"x": 600, "y": 0, "name": "Équipe agrégée"}},
        },
        # 4/6 — Une ligne par lead, puis tout regroupé
        {
            "id": 4,
            "module": "builtin:BasicFeeder",
            "version": 1,
            "parameters": {},
            "mapper": {"array": "{{1.body.data}}"},
            "metadata": {"designer": {"x": 900, "y": 0, "name": "Itérer les leads"}},
        },
        {
            "id": 6,
            "module": "builtin:BasicAggregator",
            "version": 1,
            "parameters": {"feeder": 4},
            "mapper": {"ligne": LIGNE, "record_id": "{{4.id.record_id}}"},
            "metadata": {"designer": {"x": 1200, "y": 0, "name": "Digest"}},
        },
        # 7/8 — Un seul message, et seulement s'il y a quelque chose à dire
        {
            "id": 7,
            "module": "slack:SearchUser",
            "version": 4,
            "parameters": {"__IMTCONN__": CONN_SLACK},
            "mapper": {"email": DESTINATAIRE},
            "filter": {
                "name": "Au moins un lead en souffrance",
                "conditions": [[{"a": "{{length(6.array)}}",
                                 "o": "number:greater", "b": "0"}]],
            },
            "metadata": {"designer": {"x": 1500, "y": 0, "name": "Slack - Jules"}},
        },
        {
            "id": 8,
            "module": "slack:CreateMessage",
            "version": 4,
            "parameters": {"__IMTCONN__": CONN_SLACK},
            "mapper": {
                "parse": False, "mrkdwn": True, "link_names": True,
                "channel": "{{7.id}}", "channelWType": "manualy",
                "blocks": DIGEST_BLOCKS,
                "text": "Leads non traités depuis 15 minutes",
            },
            "metadata": {"designer": {"x": 1800, "y": 0, "name": "Slack - Digest"}},
        },
        # 9/10 — Marquer, après notification : si Slack tombe, on réessaiera
        {
            "id": 9,
            "module": "builtin:BasicFeeder",
            "version": 1,
            "parameters": {},
            "mapper": {"array": "{{6.array}}"},
            "metadata": {"designer": {"x": 2100, "y": 0, "name": "Itérer pour marquer"}},
        },
        {
            "id": 10,
            "module": "attio:makeAnApiCall",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ATTIO},
            "mapper": {
                "url": f"/v2/objects/{ATTIO_OBJECT}/records/{{{{9.record_id}}}}",
                "method": "PATCH",
                "headers": [{"key": "Content-Type", "value": "application/json"}],
                "body": '{"data":{"values":{"escalade_envoyee":[{"value":true}]}}}',
            },
            "metadata": {"designer": {"x": 2400, "y": 0,
                                      "name": "Attio - Marquer escaladé"}},
        },
    ]

    return {
        "name": "[PRD] [Attio] Escalade 5 min - À la journée",
        "flow": flow,
        "metadata": {
            "instant": False,
            "version": 1,
            "scenario": {
                "dlq": False, "slots": None, "dataloss": False, "maxErrors": 3,
                "autoCommit": True, "roundtrips": 1, "sequential": False,
                "confidential": False, "freshVariables": False,
                "autoCommitTriggerLast": True,
            },
            "designer": {"orphans": []},
            "zone": "eu1.make.com",
            "notes": [],
        },
    }


SCHEDULING = {"type": "indefinitely", "interval": 300}  # toutes les 5 minutes

if __name__ == "__main__":
    bp = build()
    p = pathlib.Path(__file__).parent
    (p / "escalade-5min.blueprint.json").write_text(
        json.dumps(bp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (p / "escalade-5min.scheduling.json").write_text(
        json.dumps(SCHEDULING, indent=2) + "\n", encoding="utf-8")
    print(f"OK — {len(bp['flow'])} modules")
