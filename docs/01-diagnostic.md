# Diagnostic de l'ancienne note IA

## Le scénario en cause

| | |
|---|---|
| Nom | `[PRD] [Attio] Notes pre-réunion IA` |
| ID Make | `3448443` |
| Dossier | `Attio - Bureaux` |
| État | actif, planification « immédiatement » |
| Webhook | hook `1997221`, nommé *Attio - Nouvelle Note Enrichie* |
| Dernière modification | 27/08/2026 par Maria |

Quatre modules : webhook → Mistral (`mistral-medium-2505`) → `Transform to JSON` →
`POST /v2/notes` sur Attio.

## Ce qui ne va pas

### 1. Le modèle n'a pas accès au web

Le prompt envoyé à Mistral est :

> « J'aimerais que tu me renvoies des informations sur le prospect sur l'entreprise […]
> **Trouve moi les infos sur linkedin, le site de l'entreprise etc.** […] des posts
> linkedin récents par exemple »

Le module `mistral-ai:createACompletion` fait un simple appel de complétion : aucun outil
de recherche n'est déclaré. Le modèle ne peut donc rien « trouver ». Il fait ce qu'un
modèle fait dans ce cas : il rend le **plan** de la réponse attendue.

### 2. Résultat : des notes vides, en production

Note `a1556121-5b59-415c-9b95-aa67996ebd91`, écrite le 31/08/2026 sur un deal réel
(entreprise Vitry) :

```
### Informations sur la personne
(À compléter avec une recherche LinkedIn via le prénom, nom et email)
- Poste actuel : [À trouver]
- Ancien(s) poste(s) : [À trouver]
...
### Informations sur l'entreprise (Vitry)
- Activité : [À trouver (ex : secteur, produits/services)]
- Site web : [À trouver (ex : vitry.com)]
```

Note `52ebe4e6-2016-43ef-8e02-ddb3de404e1d`, 31/08/2026 :

```
**Informations sur la personne :**
- **Prénom & NOM :** [À compléter]
- **Poste actuel :** [À compléter via LinkedIn]
...
*À remplir avec les données trouvées sur LinkedIn, le site de l'entreprise, et autres sources publiques.*
```

Ironie du sort : sur le deal Vitry, Attio **connaissait déjà** le site (`vitry.com`),
l'effectif (51-250), le LinkedIn de la société et une description de l'activité. Ces
données n'étaient pas envoyées au modèle — le prompt ne transmet que
`person_name`, `person_email` et `company_name`.

### 3. Le monitoring ne voit rien

Toutes les exécutions récentes sont en statut `1` (succès) : l'appel Mistral réussit,
l'appel Attio réussit, la note est créée. Le scénario est vert alors qu'il ne produit
aucune valeur. C'est pour ça que le problème a pu durer.

### 4. Le déclenchement dépend d'une action humaine

Le scénario démarre sur un webhook alimenté depuis Attio. Les exécutions sont
irrégulières et concentrées sur les heures ouvrées, et les notes apparaissent plusieurs
jours après la création du deal (deal créé le 24/08, note le 31/08) : la note ne suit pas
la création du deal, elle suit un clic. C'est exactement ce qu'on veut supprimer.

## Ce que le nouveau scénario corrige

| Problème | Correction |
|---|---|
| Modèle sans accès web | Claude Opus 5 + outil `web_search`, 5 recherches max par deal |
| Contexte CRM non transmis | Le prompt injecte site, LinkedIn, effectif, description, besoin exprimé, source du lead |
| Gabarits `[À compléter]` | Règle explicite : écrire « non trouvé », interdiction des crochets et du texte générique |
| Pas de sources | Section `Sources` obligatoire avec les URL utilisées |
| Déclenchement manuel | Polling Attio toutes les 5 min sur les deals créés |
| Doublons possibles | Vérification des notes existantes avant génération |
| Échec invisible | Note non créée si le brief fait moins de 80 caractères ; DLQ activée sur le scénario |
