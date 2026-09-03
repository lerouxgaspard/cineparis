# Note IA automatique sur les nouveaux deals Attio

Remplace l'ancienne « note IA » (déclenchée à la main, et qui ne produisait que des
gabarits vides) par un **brief automatique généré sur chaque deal créé dans Attio**,
sans qu'aucun commercial n'ait à cliquer sur un bouton.

## Le problème

Le scénario Make `[PRD] [Attio] Notes pre-réunion IA` (id `3448443`) tourne toujours,
et ses exécutions sont vertes — mais les notes qu'il écrit sont inutilisables :

> **Informations sur l'entreprise (Vitry)**
> - **Activité** : [À trouver (ex : secteur, produits/services)]
> - **Actualités récentes** : Levée de fonds : [À trouver (montant, date, investisseurs)]
> - **Site web** : [À trouver (ex : vitry.com)]

Cause : le scénario demande à **Mistral** d'aller chercher des informations sur LinkedIn
et sur le site de l'entreprise, alors que le modèle n'a **aucun accès au web**. Il ne peut
donc que rendre le gabarit qu'on lui a décrit. Voir [`docs/01-diagnostic.md`](docs/01-diagnostic.md).

## La solution

Un nouveau scénario Make, **`[PRD] [Attio] Brief IA - Nouveau Deal (auto)`**, qui :

1. interroge Attio toutes les 5 minutes pour lister les deals créés dans les 30 dernières minutes ;
2. saute ceux qui ont déjà un brief (idempotent — pas de doublon) ;
3. récupère le contact et l'entreprise liés au deal ;
4. appelle **Claude Opus 5 avec l'outil de recherche web** pour un vrai travail de recherche ;
5. écrit une note `Brief IA – Prospect & Entreprise` sur le deal.

Aucun déclencheur côté commercial : le scénario va chercher les deals lui-même, donc il
n'y a ni bouton, ni workflow Attio à maintenir.

Le prompt impose au modèle d'écrire **« non trouvé »** quand une information est
introuvable, et de citer ses sources — c'est ce qui empêche le retour des `[À compléter]`.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| [`make/brief-ia-nouveau-deal.blueprint.json`](make/brief-ia-nouveau-deal.blueprint.json) | Le blueprint à importer dans Make |
| [`make/generate_blueprint.py`](make/generate_blueprint.py) | Le script qui génère ce blueprint (pour le régénérer après modification) |
| [`docs/01-diagnostic.md`](docs/01-diagnostic.md) | Pourquoi l'ancien scénario ne marche pas, preuves à l'appui |
| [`docs/02-installation.md`](docs/02-installation.md) | Import, connexions, planification, test |
| [`docs/03-desactiver-ancienne-note.md`](docs/03-desactiver-ancienne-note.md) | Comment supprimer proprement l'ancienne note IA |
| [`docs/04-prompt.md`](docs/04-prompt.md) | Le prompt, et comment l'ajuster sans casser le scénario |
| [`docs/05-exemple-brief.md`](docs/05-exemple-brief.md) | Avant / après sur un vrai deal |
| [`docs/06-couts-et-limites.md`](docs/06-couts-et-limites.md) | Coût mensuel, volumétrie, points de vigilance |

## Ce qui reste à faire côté Make

Le blueprint n'a **pas pu être installé automatiquement** : la connexion Make disponible
dans cette session est en lecture seule (aucun outil de création / modification de
scénario), et le serveur `Make - Morning RevOps Read Only` n'a pas répondu. L'import se
fait donc à la main, en cinq minutes — la procédure est dans
[`docs/02-installation.md`](docs/02-installation.md).

Toutes les briques ont été validées individuellement contre l'API Make
(`validate_blueprint_schema`, `validate_module_configuration` pour chaque module), mais
le scénario n'a jamais été exécuté : **faites tourner un « Run once » avant d'activer**.

---

# Agent « Pipeline Immo » : lire un label mail et créer le deal Attio

Second chantier, indépendant du précédent. Le scénario
[`[DEV] Pipeline Immo - Lire email - Gaspard`](https://eu1.make.com/16139/scenarios/5783201/edit)
(id 5783201) lit le label Gmail des dénonces immo et confie à un agent IA la création du
deal dans Attio. Il ne créait rien : l'agent terminait toutes ses exécutions par
« Voulez-vous que je crée automatiquement un nouveau deal ? ».

**Cause** : ses quatre outils étaient tous en lecture seule — aucun ne pouvait écrire dans
Attio. Et le module de déduplication (`Attio › List Lists`) renvoyait la liste *des listes*
du workspace, pas leur contenu, d'où la comparaison absurde entre un nom de projet et
« Liste - Bailleur, Chasse, Prospect… ».

**Point clé trouvé en route** : une dénonce immo n'est pas un enregistrement de l'objet
`deals`, c'est une **entrée de la liste Attio « Dénonce Immo »** (`team_immo`), dont l'objet
parent est `companies` et dont les attributs sont exactement Nom du projet / Statut /
Commentaires / Broker / Propriétaire.

| Fichier | Rôle |
|---|---|
| [`make/pipeline-immo-lire-email.blueprint.json`](make/pipeline-immo-lire-email.blueprint.json) | Le blueprint corrigé, à importer dans Make |
| [`make/generate_pipeline_immo_blueprint.py`](make/generate_pipeline_immo_blueprint.py) | Le script qui le génère (prompt et outils y sont modifiables) |
| [`docs/pipeline-immo/01-diagnostic.md`](docs/pipeline-immo/01-diagnostic.md) | Les 7 causes, preuves à l'appui, et où va réellement un deal immo |
| [`docs/pipeline-immo/02-installation.md`](docs/pipeline-immo/02-installation.md) | Import, connexions, les 3 réglages à faire à la main, test du doublon |
| [`docs/pipeline-immo/03-prompt-et-outils.md`](docs/pipeline-immo/03-prompt-et-outils.md) | Le prompt, les 5 outils, tous les identifiants Attio |
| [`docs/pipeline-immo/04-pieces-jointes.md`](docs/pipeline-immo/04-pieces-jointes.md) | Lire les PDF joints : pourquoi ce n'est pas branché, et comment l'ajouter |

Même réserve que ci-dessus : chaque module a été validé contre l'API Make
(`validate_module_configuration`) et la structure du blueprint aussi, mais l'accès Make de
cette session étant en lecture seule, **le scénario n'a pas été exécuté**. Un « Run once »
est indispensable avant activation.
