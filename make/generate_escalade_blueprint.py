#!/usr/bin/env python3
"""Génère le blueprint Make « [PRD] [Attio] Escalade 5 min - À la journée ».

Scénario planifié (toutes les 5 min) : le module Sleep de Make est plafonné à
300 s, un délai de 15 minutes en ligne est donc impossible — et bloquer un run
webhook 15 minutes empilerait les exécutions. L'escalade est un scénario séparé.

PRÉREQUIS : la checkbox `escalade_envoyee` doit exister sur l'objet deals_daily.
Régénérer avec :  python3 make/generate_escalade_blueprint.py
"""
import json
import pathlib

CONN_ATTIO = 3292919
CONN_SLACK = 53760

ATTIO_OBJECT = "deals_daily"
JULES_SLACK_EMAIL = "jules.b@morning.fr"
STAGE_CONTACT_ENTRANT = "Contact Entrant"
DELAI_MINUTES = 15

# Deals encore au stage d'entrée, jamais escaladés, créés il y a plus de 15 min.
QUERY_BODY = json.dumps({
    "filter": {
        "$and": [
            {"stage": {"$eq": STAGE_CONTACT_ENTRANT}},
            {"escalade_envoyee": {"$eq": False}},
            {"created_at": {
                "$lt": "{{formatDate(addMinutes(now; -%d); \"YYYY-MM-DDTHH:mm:ss[Z]\"; \"UTC\")}}"
                % DELAI_MINUTES}},
        ]
    },
    "sorts": [{"direction": "asc", "attribute": "created_at", "field": "value"}],
    "limit": 50,
}, ensure_ascii=False)

ALERTE_BLOCKS = json.dumps({"blocks": [
    {"type": "header", "text": {"type": "plain_text",
                                "text": ":warning: Lead non traité depuis 15 minutes",
                                "emoji": True}},
    {"type": "section", "fields": [
        {"type": "mrkdwn", "text": "*Deal :*\n{{2.values.name[].value}}"},
        {"type": "mrkdwn", "text": "*Commercial :*\n{{2.values.owner[].referenced_actor_id}}"},
        {"type": "mrkdwn", "text": "*Stage :*\n{{2.values.stage[].status.title}}"},
        {"type": "mrkdwn", "text": "*Créé le :*\n{{2.values.created_at[].value}}"},
    ]},
    {"type": "context", "elements": [
        {"type": "mrkdwn",
         "text": "La règle des 5 minutes n'a pas été respectée — le deal est toujours au stage d'entrée."}]},
    {"type": "actions", "elements": [
        {"type": "button",
         "text": {"type": "plain_text", "text": "Ouvrir le deal", "emoji": True},
         "url": "https://app.attio.com/morning/deals_daily/record/{{2.id.record_id}}",
         "style": "danger"}]},
]}, ensure_ascii=False, indent=1)


def build():
    flow = [
        # 1 — Attio : chercher les leads en souffrance
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
        # 2 — Un bundle par deal
        {
            "id": 2,
            "module": "builtin:BasicFeeder",
            "version": 1,
            "parameters": {},
            "mapper": {"array": "{{1.body.data}}"},
            "metadata": {"designer": {"x": 300, "y": 0, "name": "Itérer"}},
        },
        # 3 — Slack : retrouver Jules
        {
            "id": 3,
            "module": "slack:SearchUser",
            "version": 4,
            "parameters": {"__IMTCONN__": CONN_SLACK},
            "mapper": {"email": JULES_SLACK_EMAIL},
            "metadata": {"designer": {"x": 600, "y": 0, "name": "Slack - Jules"}},
        },
        # 4 — Slack : alerte
        {
            "id": 4,
            "module": "slack:CreateMessage",
            "version": 4,
            "parameters": {"__IMTCONN__": CONN_SLACK},
            "mapper": {
                "parse": False, "mrkdwn": True, "link_names": True,
                "channel": "{{3.id}}", "channelType": "im", "channelWType": "map",
                "blocks": ALERTE_BLOCKS,
                "text": "Lead non traité depuis 15 minutes",
            },
            "metadata": {"designer": {"x": 900, "y": 0, "name": "Slack - Alerter Jules"}},
        },
        # 5 — Attio : marquer, pour ne pas ré-alerter toutes les 5 minutes
        {
            "id": 5,
            "module": "attio:makeAnApiCall",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ATTIO},
            "mapper": {
                "url": f"/v2/objects/{ATTIO_OBJECT}/records/{{{{2.id.record_id}}}}",
                "method": "PATCH",
                "headers": [{"key": "Content-Type", "value": "application/json"}],
                "body": '{"data":{"values":{"escalade_envoyee":[{"value":true}]}}}',
            },
            "metadata": {"designer": {"x": 1200, "y": 0,
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
                "roundtrips": 1, "maxErrors": 3, "autoCommit": True,
                "autoCommitTriggerLast": True, "sequential": False, "slots": None,
                "confidential": False, "dataloss": False, "dlq": False,
                "freshVariables": False,
            },
            "designer": {"orphans": []},
            "zone": "eu1.make.com",
            "notes": [],
        },
    }


SCHEDULING = {"type": "indefinitely", "interval": 300}  # toutes les 5 minutes

if __name__ == "__main__":
    bp = build()
    out = pathlib.Path(__file__).parent / "escalade-5min.blueprint.json"
    out.write_text(json.dumps(bp, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    sch = pathlib.Path(__file__).parent / "escalade-5min.scheduling.json"
    sch.write_text(json.dumps(SCHEDULING, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {out}  ({len(bp['flow'])} modules)")
