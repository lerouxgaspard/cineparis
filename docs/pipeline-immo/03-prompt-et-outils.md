# Le prompt, les 5 outils, et les identifiants Attio

Tout se modifie dans [`make/generate_pipeline_immo_blueprint.py`](../../make/generate_pipeline_immo_blueprint.py),
puis on régénère :

```bash
python3 make/generate_pipeline_immo_blueprint.py
```

…et on réimporte le blueprint. (Modifier le prompt directement dans Make marche aussi ; dans
ce cas, recopiez-le dans le script pour ne pas le perdre au prochain import.)

## Ce que le prompt impose

Le prompt (constante `SYSTEM_PROMPT`) tient en 5 étapes et 3 règles. Les points qui règlent
les problèmes observés :

| Instruction | Ce qu'elle corrige |
|---|---|
| « Tu tournes dans une automatisation : personne ne peut répondre à une question. Ne demande JAMAIS de confirmation » | l'agent qui terminait par « Voulez-vous que je crée… ? » |
| Étape 2 obligatoire avant toute création, avec un **fragment** d'adresse et non l'adresse entière | le filtre `contains` d'Attio est strict : « 9 Cour des Petites Ecuries, 75010 Paris » ne matche pas « 9 Cour des Petites Écuries - 75010 » (accent, ponctuation) |
| « un expéditeur @morning.fr n'est ni le broker ni le propriétaire » | la confusion Julien Barbant / propriétaire |
| « N'invente rien : une information absente reste vide » | les `[À trouver]` et les suppositions |
| « Un email = une entrée au maximum » | double appel de l'outil de création |
| Compte-rendu en 7 lignes, format fixe | la réponse de 40 lignes illisible dans l'historique Make |

## Les 5 outils

Un outil = un module Make. Les champs écrits `{{83.nom_du_champ}}` sont les **entrées que
l'agent remplit lui-même** (83 = l'id du module agent) ; tout le reste est figé.

### 1. `Attio: Chercher un projet` — `attio:searchEntries`
Filtre `nom_du_projet` **contient** `{{83.recherche_nom_du_projet}}` sur la liste
Dénonce Immo, 10 résultats max. C'est le garde-fou anti-doublon.

### 2. `Attio: Trouver ou créer l'entreprise` — `attio:assertACompany`
Upsert sur l'attribut unique **Domains** (`97d3d667-af5b-42f6-ad10-4fe4c48fe852`) :
l'agent passe `{{83.domaine_entreprise}}` (ex. `spliit.fr`) et récupère `id.record_id`.
Seul le domaine est envoyé — volontairement : passer aussi le nom écraserait le nom
d'une société déjà renseignée dans Attio.

### 3. `Attio: Créer le deal` — `attio:createAnEntry`
Crée l'entrée dans la liste, avec la company en enregistrement parent.

| Champ Make | Entrée agent | Attribut Attio |
|---|---|---|
| `parent_record_id` | `company_record_id` | l'enregistrement parent (companies) |
| `[text]nom_du_projet` | `nom_du_projet` | Nom du projet |
| `[text]commentaires` | `commentaires` | Commentaires |
| `[number]surface` | `surface` | Surface (m²) |
| `[text]annee_du_p` | `annee_du_projet` | Année du projet |
| `[status]stage` | `statut` | Statut |
| `[status]status` | `etat` | État |

### 4. et 5. `Attio: Rattacher le broker` / `le propriétaire` — `attio:makeAnApiCall`
`PATCH /v2/lists/{liste}/entries/{{83.entry_id}}` avec
`{"data":{"entry_values":{"broker":[{"target_object":"companies","target_record_id":"…"}]}}}`.

Pourquoi un appel API et pas le module de création : les attributs `broker` et `proprietaire`
sont des **références vers companies**, et le module « Create an Entry » de Make ne les
expose pas dans son formulaire (vérifié : la liste des champs résolus par Make ne contient
ni `broker`, ni `proprietaire`, ni `responsable`). Deux outils séparés plutôt qu'un seul,
pour que l'agent puisse rattacher le broker sans avoir de propriétaire.

## Identifiants Attio du pipeline immo

À utiliser tels quels ; ils sont déjà dans le script.

```
Liste « Dénonce Immo »   a804bc1b-8ea3-44ee-8b17-505f918413aa   (api_slug: team_immo)
Objet « Companies »      45b4d831-b5f5-41db-b3e9-239c683bbe63
Attribut unique Domains  97d3d667-af5b-42f6-ad10-4fe4c48fe852
```

**Statut** (`stage`, « Où en est le projet ? ») :

| Titre | Identifiant |
|---|---|
| A visiter | `982dc62d-506f-498a-9be0-c4aa77af759d` |
| Visité | `cac94b45-a838-4438-9380-e8f74e4f3811` |
| LOI envoyé | `91d611a2-a9ab-4f96-879b-c2eac300d71a` |
| Stand-by | `efcd0617-8e7f-4f55-bc4a-22d7d7172845` |
| Signé | `2f4d6976-73a9-4955-b9d2-1af33b2c3433` |

**État** (`status`, « Où en est le dossier ») :

| Titre | Identifiant |
|---|---|
| Priorité | `4d5fa5b1-d5c8-44fc-bbde-284419d0d313` |
| En cours | `945d18ac-0aad-4ca9-8f31-12a9b1fce229` |
| Attente retour Propriétaire | `ae79f56a-afbf-4f20-9454-17096385378f` |
| Signé | `310a0159-093f-4646-a6a7-e14920bdbaed` |
| Stand-By | `7c56a631-be29-4621-9d42-91aef437f223` |

Les statuts sont donnés à l'agent **sous forme d'identifiants** dans la description de
l'outil, pas sous forme de titres : un champ « select » de Make accepte l'identifiant sans
ambiguïté, alors que le titre dépend de l'orthographe exacte (« Stand-by » vs « Stand-By »
selon l'attribut — les deux existent dans cette liste).

## Autres attributs disponibles sur la liste

Non utilisés par l'agent aujourd'hui, mais activables en ajoutant le champ au module
« Créer le deal » (`[number]loyer_facial` etc.) et une ligne au prompt :

`type_de_bail` (Durable / Éphémère / Management Contract), `loyer_facial`,
`participation_travaux`, `closing` (% de chance), `ifrs_16`, `mada`, `comite_nexity`
(À prévoir / OK / Pas de comité), `location`, `responsable` (référence membre — non exposée
par le module).

## Ajuster sans casser

- **Changer le statut par défaut** : c'est le prompt qui le dit (« valeur par défaut pour une
  nouvelle dénonce »), dans la description de l'outil `Attio: Créer le deal`.
- **Rendre le dédoublonnage plus strict** : ajouter un second appel de l'outil 1 sur un autre
  fragment (rue *et* code postal), ou remplacer `text:$contains` par une recherche sur
  `location`.
- **Sortie structurée** : passer `outputType` à `make-schema` si vous voulez brancher un
  module derrière l'agent (Slack, Sheets) avec des champs propres plutôt que du texte.
