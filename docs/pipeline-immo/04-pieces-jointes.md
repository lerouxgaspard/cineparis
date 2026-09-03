# Lire les PDF joints aux dénonces

**Ce n'est pas branché dans le blueprint livré**, et c'est un choix : la manière naïve de le
faire fait disparaître silencieusement les emails **sans** pièce jointe. Voici ce qui manque
et les deux façons propres de l'ajouter.

## Pourquoi ça ne marchait pas

- Le module *AI Agent* a bien une entrée **Input files** (`fileName` + `data`), mais elle est
  vide dans le scénario actuel (`files: []`).
- Le déclencheur `Gmail › Watch emails` ne renvoie **pas** le binaire des pièces jointes : il
  ne donne que `hasAttachment` (booléen). Le contenu s'obtient avec un second module,
  `Gmail › List email attachments and media` (`google-email:listEmailAttachments`), avec
  `Include: Attachments` et l'option avancée **Return attachment data** activée. Il renvoie
  `filename`, `mimeType`, `data`.

Autrement dit, l'instruction « lire pdf et documents si présents » du prompt d'origine était
inexécutable — l'agent n'a jamais eu le fichier entre les mains.

## Le piège à éviter

`List email attachments` est un module de type **recherche** : sur un email sans pièce
jointe, il renvoie **zéro bundle** et la route s'arrête. Si vous l'insérez simplement entre
le déclencheur et l'agent, toutes les dénonces sans PJ (la majorité, le corps de l'email
suffisant souvent) ne seront plus traitées, sans aucune erreur affichée.

## Option A — une case à cocher (le plus simple)

1. Insérer `Gmail › List email attachments and media` entre le déclencheur et l'agent :
   `Message ID` = `{{94.id}}`, `Include` = *Attachments*, et dans les options avancées
   `Return attachment data` = oui.
2. **Clic droit sur ce module → *Continue the execution of the route even if the module
   returns no results*.** C'est cette case qui évite le piège ci-dessus.
3. Ajouter un **Array aggregator** juste après (source : le module d'attachements), champ
   agrégé : `filename` et `data`.
4. Dans le module *AI Agent*, mapper **Input files** sur le résultat de l'agrégateur :
   `File name` = `filename`, `Data` = `data`.
5. Vérifier avec un email sans PJ **et** un email avec PJ : les deux doivent produire une
   exécution complète.

## Option B — un routeur (aucune case à cocher à oublier)

Déclencheur → **Router** :

- route 1, filtre `{{94.hasAttachment}}` = `true` → `List email attachments` → Array
  aggregator → agent (avec *Input files* mappé) ;
- route 2, filtre `{{94.hasAttachment}}` = `false` → agent (sans *Input files*).

Plus robuste, mais l'agent est dupliqué : deux prompts à garder synchronisés. Si vous
prenez cette option, gardez le prompt dans le script Python et régénérez les deux modules
depuis la même constante.

## Ce qu'il faut savoir avant de le faire

- **Le modèle doit savoir lire un PDF.** `gpt-5-nano` non ; les grands modèles (Claude,
  GPT-5) oui. C'est une raison de plus de changer le modèle (étape 3 de
  [`02-installation.md`](02-installation.md)).
- **Coût en tokens** : un PDF d'offre immo de quelques pages, à chaque exécution, c'est
  l'essentiel de la facture du scénario. Une plaquette scannée (images) coûte encore plus et
  se lit mal.
- **Limites Make** : voir les [prérequis des input files](https://help.make.com/input-files-for-ai-agents)
  (taille et formats acceptés dépendent du modèle).
- Cette partie **n'a pas pu être testée** depuis l'environnement où le correctif a été
  écrit (accès Make en lecture seule) : traitez la procédure comme une marche à suivre à
  valider, pas comme un acquis.

## Alternative sans PDF

Dans les dénonces observées, l'essentiel (adresse, surface, étages, disponibilité, contact
visite) est dans le **corps** de l'email ; la pièce jointe est la plaquette commerciale.
Le scénario livré exploite le corps et s'en sort sur ces cas. Ajoutez la lecture des PJ
seulement si vous constatez des dénonces où le corps ne dit rien — et dans ce cas, la
mention `Pièce(s) jointe(s) : true` déjà passée à l'agent lui permet de l'écrire dans les
commentaires, ce qui vous signale les emails à ouvrir à la main.
