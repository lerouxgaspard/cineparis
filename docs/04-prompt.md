# Le prompt, et comment l'ajuster

Le prompt vit dans le **module 6** du scénario (`Set variable` → `PROMPT`). Il est ensuite
échappé en chaîne JSON par le module 7 (`Transform to JSON`) avant d'être injecté dans le
corps de l'appel Claude, module 8, via `{{7.json}}`.

**C'est ce détour qui rend le scénario robuste** : une description d'entreprise contenant
un guillemet ou un retour à la ligne casserait le JSON si on l'interpolait directement.
Si vous modifiez le prompt, éditez le module 6 — ne touchez jamais au module 7.

## Prompt actuel

```
Tu prépares un commercial de Morning (bureaux privés et coworking à Paris) avant son premier échange avec un nouveau lead.

RÈGLES ABSOLUES
- Sers-toi de la recherche web pour vérifier chaque information. N'invente rien, ne devine pas.
- Si une information reste introuvable après recherche, écris exactement : non trouvé.
- N'écris JAMAIS de champ à compléter, de crochets, de « à trouver » ni de texte générique. Une ligne sans information vérifiée doit dire « non trouvé ».
- Distingue explicitement ce qui est un fait sourcé de ce qui est une hypothèse.
- Français, ton factuel, pas de superlatifs, 250 mots maximum au total.

DONNÉES CRM (source interne, déjà vérifiée)
- Deal : {{ifempty(2.values.name[1].value; "non renseigné")}}
- Étape : {{ifempty(2.values.stage[1].status.title; "non renseigné")}}
- Contact : {{ifempty(4.body.data[1].values.name[1].full_name; "non renseigné")}} / poste : {{ifempty(4.body.data[1].values.job_title[1].value; "non renseigné")}} / email : {{ifempty(4.body.data[1].values.email_addresses[1].email_address; "non renseigné")}} / LinkedIn : {{ifempty(4.body.data[1].values.linkedin[1].value; "non renseigné")}}
- Entreprise : {{ifempty(5.body.data[1].values.name[1].value; "non renseigné")}} / site : {{ifempty(5.body.data[1].values.domains[1].domain; "non renseigné")}} / LinkedIn : {{ifempty(5.body.data[1].values.linkedin[1].value; "non renseigné")}} / effectif Attio : {{ifempty(5.body.data[1].values.employee_range[1].option.title; "non renseigné")}}
- Description Attio de l'entreprise : {{ifempty(5.body.data[1].values.description[1].value; "non renseigné")}}
- Besoin : {{ifempty(2.values.number_of_seats[1].value; "non renseigné")}} poste(s), type de ressource : {{ifempty(2.values.resource_type[1].option.title; "non renseigné")}}
- Origine du lead : {{ifempty(2.values.deal_source[1].option.title; "non renseigné")}} / {{ifempty(2.values.source_commerce[1].option.title; "non renseigné")}}

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
La liste des URL utilisées, une par ligne. Si aucune source web n'a pu être trouvée, écris : aucune source web trouvée.
```

## Corps de l'appel Claude (module 8)

```json
{
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
}
```

## Les quatre règles qui empêchent le retour des `[À compléter]`

1. **Recherche web obligatoire** — l'outil `web_search_20260209` est déclaré dans `tools`.
   Sans lui, le modèle ne peut rien vérifier ; c'est exactement l'erreur de l'ancien scénario.
2. **« non trouvé » imposé** — une valeur manquante doit être écrite comme telle.
3. **Crochets et texte générique interdits** explicitement.
4. **Sources exigées** — une affirmation sans URL se repère immédiatement à la relecture.

Si vous réécrivez le prompt, gardez ces quatre règles.

## Ajustements courants

| Envie | Où | Quoi |
|---|---|---|
| Brief plus court / plus long | module 6 | « 250 mots maximum » |
| Ajouter un champ CRM | module 6 | ajouter une ligne `{{ifempty(2.values.<slug>[1].value; "non renseigné")}}` dans la section `DONNÉES CRM` |
| Recherche plus poussée | module 8 | `max_uses` de `5` à `8` (plus lent, plus cher) |
| Limiter à certains sites | module 8 | ajouter `"allowed_domains": ["linkedin.com", "societe.com"]` dans l'outil `web_search` |
| Réponse plus fouillée | module 8 | `"output_config": { "effort": "medium" }` — `low` est réglé pour la latence, voir `06-couts-et-limites.md` |
| Modèle moins cher | module 8 | `"model": "claude-sonnet-5"` |

## Chemins de valeurs Attio utilisés

Les valeurs d'attribut Attio sont toujours des tableaux, d'où le `[1]` (Make indexe à
partir de 1) :

| Donnée | Expression |
|---|---|
| Nom du deal | `2.values.name[1].value` |
| Étape | `2.values.stage[1].status.title` |
| Nombre de postes | `2.values.number_of_seats[1].value` |
| Type de ressource (select) | `2.values.resource_type[1].option.title` |
| Nom du contact | `4.body.data[1].values.name[1].full_name` |
| Email du contact | `4.body.data[1].values.email_addresses[1].email_address` |
| Poste du contact | `4.body.data[1].values.job_title[1].value` |
| Nom de l'entreprise | `5.body.data[1].values.name[1].value` |
| Domaine | `5.body.data[1].values.domains[1].domain` |
| Effectif (select) | `5.body.data[1].values.employee_range[1].option.title` |

Tous sont enveloppés dans `ifempty(...; "non renseigné")` : un chemin qui ne correspond à
rien dégrade le contexte, il ne casse pas le scénario.

## Extraction de la réponse (module 9)

```
{{join(map(8.body.content; "text"; "type"; "text"); newline)}}
```

Avec la recherche web activée, `content` contient plusieurs blocs (`server_tool_use`,
`web_search_tool_result`, `text`). Cette expression ne garde que les blocs `text` et les
concatène — prendre `content[1].text` renverrait souvent vide.
