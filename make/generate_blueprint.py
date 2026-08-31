# -*- coding: utf-8 -*-
"""Génère make/brief-ia-nouveau-deal.blueprint.json.

À lancer depuis la racine du dépôt :

    python3 make/generate_blueprint.py

Le blueprint est écrit à la main dans ce script plutôt que copié depuis Make, pour que le
prompt (module 6) reste relisible et modifiable en clair. Après toute modification ici,
régénérez le JSON et réimportez-le dans Make.
"""
import json, collections

ATTIO_CONN = 3292919          # "Morning - New Prod" (attio2 OAuth)
ANTHROPIC_CONN = 8495429      # à remplacer par une connexion Anthropic dédiée prod
ATTIO_RESTORE = {
    "expect": {
        "qs": {"mode": "chose"},
        "method": {"mode": "chose", "label": "POST"},
        "headers": {"mode": "chose", "items": [None]},
    },
    "parameters": {
        "__IMTCONN__": {
            "data": {"scoped": "true", "connection": "attio2"},
            "label": "Morning - New Prod",
        }
    },
}

def attio(mid, x, url, method, body=None, qs=None, filt=None, note=None):
    restore = json.loads(json.dumps(ATTIO_RESTORE))
    restore["expect"]["method"]["label"] = method
    if qs is not None:
        restore["expect"]["qs"] = {"mode": "chose", "items": [None] * len(qs)}
    mapper = {"url": url, "method": method,
              "headers": [{"key": "Content-Type", "value": "application/json"}]}
    if qs is not None:
        mapper["qs"] = qs
    if body is not None:
        mapper["body"] = body
    m = collections.OrderedDict()
    m["id"] = mid
    if filt:
        m["filter"] = filt
    m["mapper"] = mapper
    m["module"] = "attio:makeAnApiCall"
    m["version"] = 2
    m["metadata"] = {"designer": {"x": x, "y": 0, "name": note}, "restore": restore}
    m["parameters"] = {"__IMTCONN__": ATTIO_CONN}
    return m

# ---------------------------------------------------------------- 1. deals crees recemment
since_date = '{{formatDate(addMinutes(now; -30); "YYYY-MM-DD"; "UTC")}}'
since_time = '{{formatDate(addMinutes(now; -30); "HH:mm:ss"; "UTC")}}'
m1 = attio(1, 0, "/v2/objects/deals/records/query", "POST",
           body=('{\n'
                 '  "filter": {\n'
                 '    "created_at": { "$gte": "%s' % since_date + 'T' + '%s.000Z" }\n' % since_time +
                 '  },\n'
                 '  "limit": 50\n'
                 '}'),
           note="Deals créés dans les 30 dernières minutes")

# ---------------------------------------------------------------- 2. iterateur
m2 = collections.OrderedDict()
m2["id"] = 2
m2["filter"] = {"name": "Au moins un deal",
                "conditions": [[{"a": "{{1.body.data}}", "b": "0", "o": "array:greater"}]]}
m2["mapper"] = {"array": "{{1.body.data}}"}
m2["module"] = "builtin:BasicFeeder"
m2["version"] = 1
m2["metadata"] = {"designer": {"x": 300, "y": 0, "name": "Un bundle par deal"},
                  "restore": {"expect": {"array": {"mode": "edit"}}}}
m2["parameters"] = {}

# ---------------------------------------------------------------- 3. notes existantes (idempotence)
m3 = attio(3, 600, "/v2/notes", "GET",
           qs=[{"key": "parent_object", "value": "deals"},
               {"key": "parent_record_id", "value": "{{2.id.record_id}}"},
               {"key": "limit", "value": "50"}],
           note="Notes déjà présentes sur le deal")

# ---------------------------------------------------------------- 4. contact  (+ garde-fou)
guard = {
    "name": "Pas encore de brief ET quelque chose à chercher",
    "conditions": [
        [{"a": '{{join(map(3.body.data; "title"); " | ")}}', "b": "Brief IA", "o": "text:notcontain"}],
        [{"a": "{{2.values.associated_company[1].target_record_id}}", "o": "exist"},
         {"a": "{{2.values.associated_people[1].target_record_id}}", "o": "exist"}],
    ],
}
m4 = attio(4, 900, "/v2/objects/people/records/query", "POST",
           body=('{\n'
                 '  "filter": { "record_id": { "$eq": "{{2.values.associated_people[1].target_record_id}}" } },\n'
                 '  "limit": 1\n'
                 '}'),
           filt=guard, note="Contact lié au deal")

# ---------------------------------------------------------------- 5. entreprise
m5 = attio(5, 1200, "/v2/objects/companies/records/query", "POST",
           body=('{\n'
                 '  "filter": { "record_id": { "$eq": "{{2.values.associated_company[1].target_record_id}}" } },\n'
                 '  "limit": 1\n'
                 '}'),
           note="Entreprise liée au deal")

# ---------------------------------------------------------------- 6. prompt
NR = 'non renseigné'
def ie(path):
    return '{{ifempty(%s; "%s")}}' % (path, NR)

prompt = """Tu prépares un commercial de Morning (bureaux privés et coworking à Paris) avant son premier échange avec un nouveau lead.

RÈGLES ABSOLUES
- Sers-toi de la recherche web pour vérifier chaque information. N'invente rien, ne devine pas.
- Si une information reste introuvable après recherche, écris exactement : non trouvé.
- N'écris JAMAIS de champ à compléter, de crochets, de « à trouver » ni de texte générique. Une ligne sans information vérifiée doit dire « non trouvé ».
- Distingue explicitement ce qui est un fait sourcé de ce qui est une hypothèse.
- Français, ton factuel, pas de superlatifs, 250 mots maximum au total.

DONNÉES CRM (source interne, déjà vérifiée)
- Deal : {deal_name}
- Étape : {stage}
- Contact : {person_name} / poste : {job_title} / email : {email} / LinkedIn : {p_linkedin}
- Entreprise : {company_name} / site : {domain} / LinkedIn : {c_linkedin} / effectif Attio : {employee_range}
- Description Attio de l'entreprise : {c_description}
- Besoin : {seats} poste(s), type de ressource : {resource_type}
- Origine du lead : {deal_source} / {source_commerce}

FORMAT DE SORTIE (markdown, exactement ces cinq titres, dans cet ordre)

**L'entreprise**
3 puces maximum : ce qu'elle fait réellement, sa taille et son implantation, son actualité des 12 derniers mois (levée, croissance, recrutement, déménagement, nouveau marché).

**Le contact**
2 puces maximum : son rôle réel et son périmètre, son ancienneté ou son parcours quand c'est utile pour l'échange.

**Ce que ça dit du besoin**
2 puces maximum : ce que ces signaux impliquent pour une recherche de bureaux à Paris. Préfixe chaque puce par « Fait : » ou « Hypothèse : ».

**3 questions à poser**
Trois questions courtes, spécifiques à ce prospect, qu'un commercial peut poser telles quelles.

**Sources**
La liste des URL utilisées, une par ligne. Si aucune source web n'a pu être trouvée, écris : aucune source web trouvée.""".format(
    deal_name=ie("2.values.name[1].value"),
    stage=ie("2.values.stage[1].status.title"),
    person_name=ie("4.body.data[1].values.name[1].full_name"),
    job_title=ie("4.body.data[1].values.job_title[1].value"),
    email=ie("4.body.data[1].values.email_addresses[1].email_address"),
    p_linkedin=ie("4.body.data[1].values.linkedin[1].value"),
    company_name=ie("5.body.data[1].values.name[1].value"),
    domain=ie("5.body.data[1].values.domains[1].domain"),
    c_linkedin=ie("5.body.data[1].values.linkedin[1].value"),
    employee_range=ie("5.body.data[1].values.employee_range[1].option.title"),
    c_description=ie("5.body.data[1].values.description[1].value"),
    seats=ie("2.values.number_of_seats[1].value"),
    resource_type=ie("2.values.resource_type[1].option.title"),
    deal_source=ie("2.values.deal_source[1].option.title"),
    source_commerce=ie("2.values.source_commerce[1].option.title"),
)

m6 = collections.OrderedDict()
m6["id"] = 6
m6["mapper"] = {"name": "PROMPT", "scope": "roundtrip", "value": prompt}
m6["module"] = "util:SetVariable2"
m6["version"] = 1
m6["metadata"] = {"designer": {"x": 1500, "y": 0, "name": "Prompt de recherche"},
                  "restore": {"expect": {"scope": {"label": "One cycle"}}}}
m6["parameters"] = {}

# ---------------------------------------------------------------- 7. prompt -> chaine JSON echappee
m7 = collections.OrderedDict()
m7["id"] = 7
m7["mapper"] = {"object": "{{6.PROMPT}}"}
m7["module"] = "json:TransformToJSON"
m7["version"] = 1
m7["metadata"] = {"designer": {"x": 1800, "y": 0, "name": "Échappement JSON du prompt"},
                  "restore": {"parameters": {"space": {"label": "Empty"}}}}
m7["parameters"] = {"space": ""}

# ---------------------------------------------------------------- 8. Claude + recherche web
claude_body = """{
  "model": "claude-opus-5",
  "max_tokens": 4000,
  "output_config": { "effort": "low" },
  "fallbacks": "default",
  "tools": [
    {
      "type": "web_search_20260209",
      "name": "web_search",
      "max_uses": 5,
      "user_location": { "type": "approximate", "country": "FR", "city": "Paris", "timezone": "Europe/Paris" }
    }
  ],
  "messages": [
    { "role": "user", "content": {{7.json}} }
  ]
}"""
m8 = collections.OrderedDict()
m8["id"] = 8
m8["mapper"] = {
    "url": "/v1/messages",
    "method": "POST",
    "headers": [
        {"key": "content-type", "value": "application/json"},
        {"key": "anthropic-version", "value": "2023-06-01"},
        {"key": "anthropic-beta", "value": "server-side-fallback-2026-07-01"},
    ],
    "body": claude_body,
}
m8["module"] = "anthropic-claude:makeAnApiCall"
m8["version"] = 1
m8["metadata"] = {
    "designer": {"x": 2100, "y": 0, "name": "Claude Opus 5 + recherche web"},
    "restore": {
        "expect": {"qs": {"mode": "chose"},
                   "method": {"mode": "chose", "label": "POST"},
                   "headers": {"mode": "chose", "items": [None, None, None]}},
        "parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "anthropic-claude"},
                                       "label": "Anthropic Claude"}},
    },
}
m8["parameters"] = {"__IMTCONN__": ANTHROPIC_CONN}

# ---------------------------------------------------------------- 9. extraction du texte
m9 = collections.OrderedDict()
m9["id"] = 9
m9["mapper"] = {"name": "BRIEF", "scope": "roundtrip",
                "value": '{{join(map(8.body.content; "text"; "type"; "text"); newline)}}'}
m9["module"] = "util:SetVariable2"
m9["version"] = 1
m9["metadata"] = {"designer": {"x": 2400, "y": 0, "name": "Texte du brief"},
                  "restore": {"expect": {"scope": {"label": "One cycle"}}}}
m9["parameters"] = {}

# ---------------------------------------------------------------- 10. brief -> chaine JSON echappee
m10 = collections.OrderedDict()
m10["id"] = 10
m10["mapper"] = {"object": "{{9.BRIEF}}"}
m10["module"] = "json:TransformToJSON"
m10["version"] = 1
m10["metadata"] = {"designer": {"x": 2700, "y": 0, "name": "Échappement JSON du brief"},
                   "restore": {"parameters": {"space": {"label": "Empty"}}}}
m10["parameters"] = {"space": ""}

# ---------------------------------------------------------------- 11. note Attio
m11 = attio(11, 3000, "/v2/notes", "POST",
            body=('{\n'
                  '  "data": {\n'
                  '    "parent_object": "deals",\n'
                  '    "parent_record_id": "{{2.id.record_id}}",\n'
                  '    "title": "Brief IA – Prospect & Entreprise",\n'
                  '    "format": "markdown",\n'
                  '    "content": {{10.json}}\n'
                  '  }\n'
                  '}'),
            filt={"name": "Brief non vide",
                  "conditions": [[{"a": "{{length(9.BRIEF)}}", "b": "80", "o": "number:greater"}]]},
            note="Création de la note sur le deal")

blueprint = {
    "name": "[PRD] [Attio] Brief IA - Nouveau Deal (auto)",
    "flow": [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11],
    "metadata": {
        "instant": False,
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
            "dlq": True,
            "freshVariables": False,
        },
        "designer": {"orphans": []},
        "zone": "eu1.make.com",
        "notes": [],
    },
}

with open("make/brief-ia-nouveau-deal.blueprint.json", "w") as f:
    json.dump(blueprint, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("ok")
