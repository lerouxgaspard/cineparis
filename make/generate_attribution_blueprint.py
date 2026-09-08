#!/usr/bin/env python3
"""Génère le blueprint Make « [PRD] [Attio] Attribution agentique - À la journée ».

Toutes les constantes ci-dessous ont été relevées sur l'instance réelle
(Attio, Airtable, Slack, Make) — voir docs/10-attribution-agentique.md.
Régénérer avec :  python3 make/generate_attribution_blueprint.py
"""
import json
import pathlib

# --- Connexions Make (team 16139) -------------------------------------------
CONN_ATTIO = 3292919      # Morning - New Prod (benoit@novlini.io)
CONN_AIRTABLE = 2426866
CONN_SLACK = 53760        # Robot Bidule (bidule)
CONN_AI = 9767251         # Gaspard's Make's AI Provider connection

# --- Attio -------------------------------------------------------------------
ATTIO_OBJECT = "deals_daily"
JULES_ID = "e1ddf2ca-504e-4510-b53d-1d7fb16d9f96"
STAGE_CONTACT_ENTRANT = "edd12aa0-7e9c-4478-ab45-042534c1bc4a"

# --- Airtable ----------------------------------------------------------------
AT_BASE = "app1ZLIN13lGG0cPE"
AT_TABLE = "tbl362A2eveuwpuBE"          # Equipe_Daily
AT_FLD_DERNIER_LEAD = "fldmq0SDLFYe3gJoS"

# --- Slack -------------------------------------------------------------------
SLACK_CHANNEL_JOURNEE = "C084VQ7D6B0"   # #100sdr (24 membres, Robot Bidule déjà dedans)

SEUIL_VALEUR = 5000

# Palier du Make AI Provider. "large" = gpt-5-mini (reasoning low).
AGENT_MODEL = "large"

SYSTEM_PROMPT = """Tu es un assistant de qualification de leads pour Morning, \
un opérateur d'espaces de travail. Tu analyses UN lead entrant sur l'offre \
« à la journée » (coworking, bureau à la journée, salle de réunion / SDR).

Ton unique travail est de LIRE et de RESTITUER des faits. Tu ne choisis pas de \
commercial : l'attribution est décidée par une règle en aval.

Tu reçois les champs structurés du deal et le texte libre des notes qui y sont \
rattachées. Tu dois produire :

1. recurrence_detected — true si, et seulement si, le texte ou les champs \
indiquent un besoin QUI SE RÉPÈTE dans le temps : « toutes les semaines », \
« tous les mois », « chaque mardi », « récurrent », « abonnement », \
« contrat cadre », « on reviendra régulièrement », « x fois par mois ».
   Une réservation unique portant sur plusieurs jours consécutifs n'est PAS \
récurrente. Un simple « on reviendra peut-être » n'est PAS récurrent. \
Dans le doute, réponds false.

2. recurrence_frequency — l'une de : Hebdomadaire, Mensuel, Annuel, Ponctuel, \
A qualifier. Mets « A qualifier » si recurrence_detected est true mais que la \
fréquence n'est pas explicite.

3. valeur_estimee — la valeur en euros. Utilise le champ « value » du deal s'il \
est renseigné et supérieur à 0. Sinon, et seulement sinon, estime à partir du \
nombre de participants, de la durée et du type de ressource, et signale-le dans \
la justification. Ne renvoie jamais null : renvoie 0 si tu ne peux rien estimer.

4. confiance — de 0 à 100, ta confiance dans recurrence_detected.

5. justification — deux phrases maximum, en français. Si recurrence_detected \
est true, CITE la phrase exacte du texte qui le prouve, entre guillemets. \
Si tu n'as rien trouvé, écris « aucun indice de récurrence dans les notes ». \
N'invente jamais une citation.

Règle absolue : n'affirme rien qui ne soit pas dans les données fournies. \
Si une information manque, dis qu'elle manque."""

AGENT_OUTPUT_SCHEMA = [
    {"name": "recurrence_detected", "type": "boolean",
     "label": "Besoin récurrent détecté", "required": True},
    {"name": "recurrence_frequency", "type": "text",
     "label": "Fréquence", "multiline": False, "required": False},
    {"name": "valeur_estimee", "type": "number",
     "label": "Valeur estimée (EUR)", "required": True},
    {"name": "confiance", "type": "number",
     "label": "Confiance (0-100)", "required": False},
    {"name": "justification", "type": "text",
     "label": "Justification", "multiline": True, "required": True},
]

AGENT_INPUT = """### Champs du deal
- Record ID : {{1.deal_id}}
- Nom : {{2.body.data.values.name[].value}}
- Type de ressource : {{2.body.data.values.type_de_ressource[].option.title}}
- Type d'offre : {{2.body.data.values.type_offre_daily[].option.title}}
- Valeur (champ « value ») : {{2.body.data.values.value[].currency_value}} EUR
- Participants (pax) : {{2.body.data.values.pax[].value}}
- Durée (jours) : {{2.body.data.values.duration_deal_daily[].value}}
- Date de début : {{2.body.data.values.date_start_deal_daily[].value}}
- Fréquence déjà saisie : {{2.body.data.values.recurrence_frequency[].option.title}}
- Case « récurrent » déjà cochée : {{2.body.data.values.recurrence_detected[].value}}

### Notes rattachées (texte libre)
{{join(map(3.body.data; "content_plaintext"); "

---

")}}

Analyse ce lead et renvoie la structure demandée."""


def designer(x, y=0, name=None):
    d = {"designer": {"x": x, "y": y}}
    if name:
        d["designer"]["name"] = name
    return d


def attio_call(mid, x, url, method, body=None, name=None, flt=None):
    mapper = {
        "url": url,
        "method": method,
        "headers": [{"key": "Content-Type", "value": "application/json"}],
    }
    if body is not None:
        mapper["body"] = body
    mod = {
        "id": mid,
        "module": "attio:makeAnApiCall",
        "version": 2,
        "parameters": {"__IMTCONN__": CONN_ATTIO},
        "mapper": mapper,
        "metadata": designer(x, 0, name),
    }
    if flt:
        mod["filter"] = flt
    return mod


def set_vars(mid, x, variables, name=None, y=0):
    return {
        "id": mid,
        "module": "util:SetVariables",
        "version": 1,
        "parameters": {},
        "mapper": {
            "variables": [{"name": k, "value": v} for k, v in variables],
            "scope": "roundtrip",
        },
        "metadata": designer(x, y, name),
    }


def build():
    flow = []

    # 1 — Webhook
    flow.append({
        "id": 1,
        "module": "gateway:CustomWebHook",
        "version": 1,
        "parameters": {},
        "mapper": {},
        "metadata": designer(0, 0, "Nouveau lead à la journée"),
    })

    # 2 — Attio : lire le deal
    flow.append(attio_call(
        2, 300,
        f"/v2/objects/{ATTIO_OBJECT}/records/{{{{1.deal_id}}}}",
        "GET", name="Attio - Lire le deal"))

    # 3 — Attio : lire les notes (garde-fou : on s'arrête ici si non traitable)
    flow.append(attio_call(
        3, 600,
        "/v2/notes?limit=25&parent_object=" + ATTIO_OBJECT
        + "&parent_record_id={{1.deal_id}}",
        "GET", name="Attio - Lire les notes",
        flt={
            "name": "Lead traitable par un commercial",
            "conditions": [[
                {"a": "{{2.body.data.values.type_de_ressource[].option.title}}",
                 "o": "text:notequal", "b": "Coworking à la journée"},
                {"a": "{{2.body.data.values.admin_automation_stop[].option.title}}",
                 "o": "text:notequal", "b": "Yes"},
            ]],
        }))

    # 4 — Airtable : pool de commerciaux (Jules inclus)
    flow.append({
        "id": 4,
        "module": "airtable:ActionSearchRecords",
        "version": 3,
        "parameters": {"__IMTCONN__": CONN_AIRTABLE},
        "mapper": {
            "base": AT_BASE,
            "table": AT_TABLE,
            "formula": "AND({actif}=1, OR({est_absent}=0, {est_absent}=BLANK()))",
            "maxRecords": 20,
            "sort": [{"field": "dernier_lead_daily", "direction": "asc"}],
            "useColumnId": False,
        },
        "metadata": designer(900, 0, "Airtable - Pool commerciaux"),
    })

    # 5 — Agrégateur du pool
    flow.append({
        "id": 5,
        "module": "builtin:BasicAggregator",
        "version": 1,
        "parameters": {"feeder": 4},
        "mapper": {"id": "{{4.id}}", "name": "{{4.name}}", "mail": "{{4.mail}}",
                   "attio_user_id": "{{4.attio_user_id}}"},
        "metadata": designer(1200, 0, "Pool agrégé"),
    })

    # 6 — L'agent : il LIT, il ne décide pas
    flow.append({
        "id": 6,
        "module": "ai-local-agent:RunLocalAIAgent",
        "version": 0,
        "tools": [],
        "parameters": {"makeConnectionId": CONN_AI},
        "mapper": {
            "systemPrompt": SYSTEM_PROMPT,
            "message": AGENT_INPUT,
            "files": [],
            "threadId": "",
            "outputType": "make-schema",
            "outputSchema": AGENT_OUTPUT_SCHEMA,
            # Relevés sur le scénario 7299000 après réglage manuel du modèle.
            # Le RPC RpcGetModels est refusé hors contexte organisation, donc ces
            # valeurs ne sont pas découvrables depuis l'extérieur : sans elles,
            # l'import échoue sur « config.llmConfig.llmModel Required ».
            # "large" = gpt-5-mini, reasoning low, réservé aux plans payants.
            "defaultModel": AGENT_MODEL,
            "tokenLimit": "50",
            "promptCaching": "none",
            "fallbackEnabled": False,
            "modelConfig": {
                "timeout": "",
                "recursionLimit": "300",
                "iterationsFromHistoryCount": "10",
            },
        },
        "metadata": designer(1500, 0, "Agent - Lecture du besoin"),
    })

    # 7 — Normalisation (une seule fois, pas de scoring)
    flow.append(set_vars(7, 1800, [
        ("deal_value",
         "{{ifempty(get(first(2.body.data.values.value); \"currency_value\"); "
         "ifempty(6.jsonResponse.valeur_estimee; 0))}}"),
        ("recurrence", "{{ifempty(6.jsonResponse.recurrence_detected; false)}}"),
        ("rr_id", "{{first(map(5.array; \"attio_user_id\"))}}"),
        ("rr_rec", "{{first(map(5.array; \"id\"))}}"),
        ("rr_mail", "{{first(map(5.array; \"mail\"))}}"),
        ("rr_name", "{{first(map(5.array; \"name\"))}}"),
        # Aplatis pour Slack. Les blocks sont du JSON : un retour à la ligne brut
        # dans une valeur interpolée casse le parsing (« Bad control character in
        # string literal », échecs du 08/09 à 12:58 et 13:26). La justification de
        # l'agent est déclarée multiline, elle arrive donc sur plusieurs lignes.
        ("justification_txt",
         "{{replace(ifempty(6.jsonResponse.justification; \" \"); "
         "\"/[\\r\\n\\t]+/g\"; \" \")}}"),
        ("deal_name_txt",
         "{{replace(ifempty(2.body.data.values.name[].value; \"inconnue\"); "
         "\"/[\\r\\n\\t]+/g\"; \" \")}}"),
    ], name="Normalisation"))

    # 8 — La décision : deux branches explicites
    flow.append({
        "id": 8,
        "module": "builtin:BasicIfElse",
        "version": 1,
        "mapper": None,
        "metadata": designer(2100, 0, "Décision d'attribution"),
        "branches": [
            {
                "merge": True,
                "label": f"Prioritaire (> {SEUIL_VALEUR} EUR ou récurrent) -> Jules",
                "type": "condition",
                "conditions": [
                    [{"a": "{{7.deal_value}}", "o": "number:greater",
                      "b": str(SEUIL_VALEUR)}],
                    [{"a": "{{7.recurrence}}", "o": "boolean:equal", "b": "true"}],
                ],
                "flow": [set_vars(9, 2400, [
                    ("assignee_id", JULES_ID),
                    ("assignee_rec", "{{first(map(5.array; \"id\"; \"attio_user_id\"; \"" + JULES_ID + "\"))}}"),
                    ("assignee_mail", "jules.b@morning.fr"),
                    ("assignee_name", "Jules Bornhauser"),
                    ("attribution_mode", "Prioritaire"),
                ], name="Attribution Jules", y=-150)],
            },
            {
                "merge": True,
                "disabled": False,
                "label": "Round robin",
                "type": "else",
                "flow": [set_vars(10, 2400, [
                    ("assignee_id", "{{7.rr_id}}"),
                    ("assignee_rec", "{{7.rr_rec}}"),
                    ("assignee_mail", "{{7.rr_mail}}"),
                    ("assignee_name", "{{7.rr_name}}"),
                    ("attribution_mode", "Round robin"),
                ], name="Attribution rotation", y=150)],
            },
        ],
    })

    # 11 — Merge
    flow.append({
        "id": 11,
        "module": "builtin:BasicMerge",
        "version": 1,
        "mapper": None,
        "metadata": designer(2700, 0),
        "outputs": [],
        "filters": [None, None],
    })

    # 12 — Relecture des variables posées dans la branche gagnante
    flow.append({
        "id": 12,
        "module": "util:GetVariables",
        "version": 1,
        "parameters": {},
        "mapper": {"variables": ["assignee_id", "assignee_rec", "assignee_mail",
                                 "assignee_name", "attribution_mode"]},
        "metadata": designer(3000, 0, "Assigné retenu"),
    })

    # 13 — Attio : écrire owner + récurrence + justification
    patch_body = (
        '{"data":{"values":{'
        '"owner":[{"referenced_actor_type":"workspace-member",'
        '"referenced_actor_id":"{{12.assignee_id}}"}],'
        '"recurrence_detected":[{"value":{{7.recurrence}}}],'
        '"value":[{"currency_value":{{7.deal_value}}}]'
        '}}}'
    )
    flow.append(attio_call(
        13, 3300, f"/v2/objects/{ATTIO_OBJECT}/records/{{{{1.deal_id}}}}",
        "PATCH", body=patch_body, name="Attio - Assigner le deal"))

    # 14 — Airtable : renvoyer l'assigné en fin de rotation (Jules compris)
    flow.append({
        "id": 14,
        "module": "airtable:ActionUpdateRecords",
        "version": 3,
        "parameters": {"__IMTCONN__": CONN_AIRTABLE},
        "mapper": {
            "id": "{{12.assignee_rec}}",
            "base": AT_BASE,
            "table": AT_TABLE,
            "record": {AT_FLD_DERNIER_LEAD: "{{now}}"},
            "typecast": False,
            "useColumnId": True,
        },
        "metadata": designer(3600, 0, "Airtable - Fin de rotation"),
    })

    # 15 — Slack : retrouver l'utilisateur
    flow.append({
        "id": 15,
        "module": "slack:SearchUser",
        "version": 4,
        "parameters": {"__IMTCONN__": CONN_SLACK},
        "mapper": {"email": "{{12.assignee_mail}}"},
        "metadata": designer(3900, 0, "Slack - Trouver le commercial"),
    })

    # Pas de DM au commercial : retiré le 08/09, le canal #100sdr suffit et le
    # module posait des erreurs à répétition. La mention <@id> dans le message
    # canal notifie déjà la personne concernée, donc la règle des 5 minutes
    # reste tenable. Le module SearchUser (15) est conservé : c'est lui qui
    # fournit l'identifiant Slack utilisé par la mention.

    # 18 — Attio : tâche liée AU BON deal
    task_body = (
        '{"data":{'
        '"content":"Nouveau deal entrant - Call prise de brief",'
        '"format":"plaintext",'
        '"deadline_at":"{{formatDate(now; \\"YYYY-MM-DDTHH:mm:ssZ\\")}}",'
        '"is_completed":false,'
        '"linked_records":[{"target_object":"' + ATTIO_OBJECT + '",'
        '"target_record_id":"{{1.deal_id}}"}],'
        '"assignees":[{"referenced_actor_type":"workspace-member",'
        '"referenced_actor_id":"{{12.assignee_id}}"}]}}'
    )
    flow.append(attio_call(
        18, 4500, "/v2/tasks", "POST", body=task_body,
        name="Attio - Créer la tâche"))

    # 17 — Slack : notification canal
    chan_blocks = json.dumps({"blocks": [
        {"type": "header", "text": {"type": "plain_text",
                                    "text": ":rotating_light: Nouveau lead à la journée",
                                    "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": "*Pour <@{{15.id}}>* — attribution : {{12.attribution_mode}}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": "*Produit :*\n{{2.body.data.values.type_de_ressource[].option.title}}"},
            {"type": "mrkdwn", "text": "*Participants :*\n{{ifempty(2.body.data.values.pax[].value; \"non précisé\")}}"},
            {"type": "mrkdwn", "text": "*Date :*\n{{ifempty(2.body.data.values.date_start_deal_daily[].value; \"à préciser\")}}"},
            {"type": "mrkdwn", "text": "*Société :*\n{{7.deal_name_txt}}"},
            {"type": "mrkdwn", "text": "*Valeur estimée :*\n{{7.deal_value}} EUR"},
            {"type": "mrkdwn", "text": "*Récurrent :*\n{{if(7.recurrence; \"oui\"; \"non\")}}"},
        ]},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": ":robot_face: {{7.justification_txt}}"}]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Ouvrir le deal", "emoji": True},
             "url": "{{2.body.data.web_url}}", "style": "primary"}]},
        {"type": "context", "elements": [
            {"type": "mrkdwn",
             "text": ":stopwatch: *À traiter en moins de 5 minutes* — réagis à ce message."}]},
    ]}, ensure_ascii=False, indent=1)

    flow.append({
        "id": 17,
        "module": "slack:CreateMessage",
        "version": 4,
        "parameters": {"__IMTCONN__": CONN_SLACK},
        "mapper": {
            "parse": False, "mrkdwn": True, "link_names": True,
            "channel": SLACK_CHANNEL_JOURNEE,
            "channelType": "public", "channelWType": "list",
            "blocks": chan_blocks,
            "text": "Nouveau lead à la journée",
        },
        "metadata": designer(4800, 0, "Slack - #100sdr"),
        # Le DM au commercial (16) et la tâche Attio (18) sont le coeur du flux :
        # s'ils échouent, le scénario DOIT échouer bruyamment. Le post canal est
        # une diffusion de confort — un bot désinvité ou un canal archivé ne doit
        # pas laisser un deal assigné sans tâche, comme c'est arrivé le 08/09.
        "onerror": [{
            "id": 20,
            "module": "builtin:Ignore",
            "version": 1,
            "parameters": {},
            "mapper": {},
            "metadata": designer(4800, 150, "Ignorer l'échec de diffusion"),
        }],
    })

    # Pas de module Webhook Response : Make refuse de l'exécuter dès lors que
    # la requête a transité par la file du webhook plutôt que d'être traitée sur
    # la connexion vivante — « Response can't be processed when scenario is not
    # executed immediately on data arrival », avertissement observé sur
    # l'exécution 9067e9b6ee364b9f92a95a6b8fdac1a5 du 08/09. La réponse n'était
    # donc jamais délivrée, et l'appelant (une automatisation Attio) ne la lit pas.

    return {
        "name": "[PRD] [Attio] Attribution agentique - À la journée",
        "flow": flow,
        "metadata": {
            "instant": True,
            "version": 1,
            "scenario": {
                "roundtrips": 1,
                "maxErrors": 3,
                "autoCommit": True,
                "autoCommitTriggerLast": True,
                "sequential": False,
                "slots": None,
                "confidential": False,
                "dataloss": False,
                "dlq": False,
                "freshVariables": False,
            },
            "designer": {"orphans": []},
            "zone": "eu1.make.com",
            "notes": [],
        },
    }


if __name__ == "__main__":
    bp = build()
    out = pathlib.Path(__file__).parent / "attribution-agentique.blueprint.json"
    out.write_text(json.dumps(bp, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"OK -> {out}  ({len(bp['flow'])} modules de premier niveau)")
