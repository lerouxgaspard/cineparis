# Installation du scénario corrigé

Fichier à importer : [`make/pipeline-immo-lire-email.blueprint.json`](../../make/pipeline-immo-lire-email.blueprint.json)

Le blueprint a été validé contre l'API Make (structure + configuration de chaque module),
mais **il n'a jamais été exécuté** : la connexion Make disponible ici est en lecture seule.
Faites un « Run once » avant d'activer.

## 1. Importer

Deux options.

**A — remplacer le scénario existant** (garde l'URL `…/scenarios/5783201/edit`) :
ouvrir le scénario → menu `⋯` en bas → *Import Blueprint* → coller le fichier.
L'ancien flux est remplacé ; pensez à noter au préalable ce que vous voulez garder.

**B — créer un nouveau scénario** : *Create a new scenario* → `⋯` → *Import Blueprint*.
Recommandé pour comparer les deux côte à côte, l'ancien restant en pause.

## 2. Vérifier les connexions

Les identifiants de connexion de l'équipe Morning sont déjà inscrits dans le blueprint :

| Module | Connexion attendue |
|---|---|
| Gmail › Watch emails | `My Gmail connection (gaspard.l@morning.fr)` — id 7498409 |
| AI Agent | `Gaspard's Make's AI Provider connection` — id 9767251 |
| Les 5 outils Attio | `Gaspard's Attio OAuth connection (gaspard.l@morning.fr)` — id 10415895 |

Si Make affiche un champ de connexion vide après l'import, re-sélectionnez-la dans la liste.

> **Le label lu est celui du déclencheur** : `Projet_pipeline_immo`, dans la boîte
> gaspard.l@morning.fr. L'ancien scénario avait un outil qui lisait, lui, le label
> `0 - Dénonce Immo` de la boîte **julien@morning.fr**. Si la vraie source des dénonces est
> celle de Julien, changez la connexion **et** le label du module 94 — et rien d'autre.

## 3. Les 3 réglages à faire à la main

1. **Choisir le modèle.** Ouvrir le module *AI Agent* → champ **Model** → prendre le grand
   modèle (Claude Sonnet/Opus, ou GPT-5 selon ce que propose la connexion). Le blueprint
   arrive avec `medium` (= `gpt-5-nano`), qui est la valeur actuelle : trop juste pour
   extraire des informations d'un email et enchaîner 4 appels d'outils. La liste des modèles
   dépend de la connexion, elle ne peut pas être écrite dans le blueprint.
2. **Planification** : 15 minutes (`Every 15 minutes`), comme aujourd'hui.
3. **Vérifier le champ *Maximum output length*** : le blueprint le met à 100 % (il était à
   50 %, ce qui tronquait les réponses).

## 4. Tester

1. Mettre le scénario **en pause**, puis *Run once*.
2. S'il ne se déclenche pas : le déclencheur Gmail est *polling*, il ne voit que les emails
   **arrivés après** le dernier repère. Utiliser *Choose where to start* → *From now on*,
   puis se réenvoyer une dénonce sur le label.
3. Ouvrir la bulle du module *AI Agent* et lire :
   - **Response** : le compte-rendu en 7 lignes (`Action : créé | doublon | bloqué`) ;
   - **Metadata › Execution steps** : la suite des outils appelés. Sur une dénonce complète
     on attend : `Chercher un projet` → `Trouver ou créer l'entreprise` → `Créer le deal`
     → `Rattacher le broker` (+ `Rattacher le propriétaire` si nommé).
4. Vérifier dans Attio : liste **Dénonce Immo**, l'entrée doit porter le nom du projet, le
   statut *A visiter*, l'état *En cours*, la surface et les commentaires.
5. Relancer le scénario sur **le même email** : la deuxième exécution doit répondre
   `Action : doublon` et ne rien créer. C'est le test qui compte.

## 5. Pièges connus

- **Test avec un email transféré** : si vous vous transférez une dénonce depuis
  votre propre boîte, l'expéditeur devient `@morning.fr`. Le prompt sait ignorer ce cas et
  chercher l'email d'origine dans le corps, mais s'il n'y en a pas, l'agent s'arrêtera sur
  `Action : bloqué` — c'est le comportement voulu, pas un bug.
- **Domaine générique** : une dénonce envoyée depuis une adresse Gmail ne crée rien
  (l'entreprise ne peut pas être identifiée par son domaine). L'agent le signale.
- **`Créer le deal` appelé deux fois** : ne devrait pas arriver (règle explicite dans le
  prompt), mais si vous le voyez dans *Execution steps*, baissez *Steps per agent call*
  (25 aujourd'hui) et vérifiez que le grand modèle est bien sélectionné.
- **Coût** : un email = 1 opération Gmail + 1 appel agent + 2 à 5 appels d'outils Attio.
  Comptez ~8 opérations Make par dénonce, plus les tokens du modèle.

## 6. Ce qui n'est pas dans ce scénario

- La lecture des **pièces jointes** (PDF de l'offre) : voir
  [`04-pieces-jointes.md`](04-pieces-jointes.md).
- Le champ **Responsable Projet** : c'est une référence vers un membre du workspace, que le
  module Make « Create an Entry » n'expose pas. À mettre à la main, ou à ajouter sur le même
  modèle que les outils de rattachement (appel API).
- Le passage de l'email en « traité » (retrait du label, ou pose d'un label `traité`) :
  utile pour l'idempotence si vous relancez souvent le scénario à la main. Module
  `Gmail › Update email labels`, à brancher après l'agent.
