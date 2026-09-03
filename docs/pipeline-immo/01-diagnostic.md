# Pourquoi l'agent ne crée aucun deal

Scénario analysé : **`[DEV] Pipeline Immo - Lire email - Gaspard`**
([id 5783201](https://eu1.make.com/16139/scenarios/5783201/edit), équipe Morning 16139),
tel qu'il était configuré le 3 septembre 2026.

La réponse de l'agent (« Voulez-vous que je crée automatiquement un nouveau deal… ? »)
n'est pas un problème de prompt : **l'agent n'a aucun outil capable d'écrire dans Attio.**
Il ne pouvait littéralement rien faire d'autre que demander.

## Ce que contient le scénario aujourd'hui

| # | Module | Rôle réel |
|---|---|---|
| 94 | Gmail › Watch emails, label `Projet_pipeline_immo` | déclencheur — OK |
| 83 | AI Agent (`gpt-5-nano`, reasoning low) | l'agent, avec 4 outils |
| 88 | **Attio › Update a List** | modifie les *droits* de la liste — à supprimer |

Les 4 outils de l'agent :

| Outil | Module | Problème |
|---|---|---|
| Gmail: Search emails | `google-email:executeEmailSearchQuery` | cherche dans un **autre** label (`0 - Dénonce Immo`) et une **autre** boîte (julien@morning.fr) que le déclencheur |
| Attio: List Lists | `attio:listLists` | renvoie la liste **des listes** (Bailleur, Chasse, Prospect…), pas leur contenu |
| Attio: Get a Company | `attio:getACompany` | exige un `record_id` que l'agent n'a jamais |
| Attio: Get a Person | `attio:getAPerson` | idem |

## Les 7 causes, dans l'ordre d'importance

1. **Aucun outil d'écriture.** Pas de `Create an Entry`, pas de `Create a Record`. Un agent
   qui n'a que des outils de lecture ne peut que rédiger une proposition — c'est exactement
   ce qu'il a fait.

2. **Le mauvais module pour la déduplication.** `List Lists` renvoie les métadonnées des
   9 listes du workspace. D'où la phrase de l'agent : « les listes actuelles incluent
   Liste - Bailleur, Chasse, Prospect… » — il comparait un nom de projet à des noms de
   listes. Le bon module est `Search Entries`, filtré sur la liste **Dénonce Immo** et sur
   l'attribut `nom_du_projet`.

3. **Deux outils inutilisables par construction.** `Get a Company` / `Get a Person`
   prennent un identifiant Attio en entrée. L'agent le dit lui-même dans son raisonnement :
   *« The tool requires an ID for searching, which is a bit tricky »*. Pour retrouver une
   société à partir d'un nom ou d'un domaine il faut `Create or Update a Company`
   (upsert sur le domaine) ou un appel API `POST /v2/objects/companies/records/query`.

4. **Le module 88 est dangereux.** `Attio › Update a List` sur la liste
   `a804bc1b-8ea3-44ee-8b17-505f918413aa` avec `workspace_access: read-and-write` :
   à chaque exécution, le scénario réécrit les **permissions** de la liste Dénonce Immo.
   Il ne crée rien. C'est vraisemblablement un module choisi par erreur à la place de
   « Create an Entry ».

5. **Le modèle est trop petit.** `gpt-5-nano`, reasoning *low*, sortie limitée à 50 %.
   Symptôme visible dans la trace : le même bloc de raisonnement est répété à
   l'identique et `Attio: List Lists` est appelé deux fois de suite.

6. **Les pièces jointes n'arrivent jamais à l'agent.** Le champ *Input files* du module 83
   est vide (`files: []`) et le déclencheur Gmail ne renvoie pas le binaire des pièces
   jointes. L'instruction « lire pdf et documents si présents » était donc impossible à
   exécuter. Voir [`04-pieces-jointes.md`](04-pieces-jointes.md).

7. **Le prompt ne fixe aucun contrat.** Une phrase (« Ton but est d'aller dans les mails,
   checker si il y a de nouvelles dénonces… ») : pas de champs attendus, pas de règle de
   dédoublonnage, pas d'interdiction de poser des questions, pas de « n'invente rien ».
   D'où la confusion entre Julien Barbant (qui **transfère** l'email) et le propriétaire du
   bien, et la liste d'« actions recommandées » à la place d'une action.

## Où va réellement un « deal » du pipeline immo

C'est le point qui manquait à l'agent. Dans ce workspace Attio, une dénonce immo **n'est pas
un enregistrement de l'objet `deals`** (dont les étapes sont Contact Entrant, Lead Qualifié,
A Visité, Contrat Envoyé, Won, Lost). C'est une **entrée de la liste « Dénonce Immo »**
(`api_slug: team_immo`, id `a804bc1b-8ea3-44ee-8b17-505f918413aa`), dont l'objet parent est
`companies`, et dont les attributs d'entrée sont précisément ceux demandés :

| Demandé | Attribut d'entrée | Type |
|---|---|---|
| Nom du projet | `nom_du_projet` | texte |
| Statut (A visiter, Visité, LOI envoyé, Stand-by, Signé) | `stage` | statut |
| Commentaires | `commentaires` | texte |
| Broker | `broker` | référence → companies |
| Propriétaire | `proprietaire` | référence → companies |
| Company | l'enregistrement **parent** de l'entrée | companies |

Les 5 valeurs de `stage` correspondent mot pour mot à celles listées dans la description de
l'outil Gmail du scénario : c'est bien cette liste qui est la cible.

Le reste des attributs disponibles (surface, loyer facial, type de bail, % closing, IFRS 16,
MADA, participation travaux, comité Nexity, année du projet, responsable projet, État) est
documenté dans [`03-prompt-et-outils.md`](03-prompt-et-outils.md).

## Le correctif

Un blueprint corrigé : [`../../make/pipeline-immo-lire-email.blueprint.json`](../../make/pipeline-immo-lire-email.blueprint.json).

- module 88 supprimé ;
- les 4 outils remplacés par 5 outils qui fonctionnent (chercher un projet, trouver/créer
  l'entreprise, créer l'entrée, rattacher le broker, rattacher le propriétaire) ;
- un prompt qui impose le dédoublonnage, interdit les questions et fixe le format du
  compte-rendu ;
- l'email est passé à l'agent sous forme lisible (expéditeur, objet, date, corps) au lieu du
  bundle brut `{{94}}`.

Installation : [`02-installation.md`](02-installation.md).
