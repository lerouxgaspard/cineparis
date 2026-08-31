# Supprimer l'ancienne note IA

À faire **après** avoir vérifié que le nouveau scénario écrit des briefs corrects
(cf. `02-installation.md`, étape 4). Tant que l'ancien tourne encore, on peut comparer.

## 1. Couper le scénario Make

`[PRD] [Attio] Notes pre-réunion IA` — id **`3448443`**, dossier `Attio - Bureaux`.

1. Basculer le scénario sur **OFF**.
2. Le renommer `[DÉPRÉCIÉ 2026-08-31] [Attio] Notes pre-réunion IA` — l'équipe voit
   immédiatement qu'il ne faut plus s'en servir.
3. Attendre une semaine, vérifier qu'aucun scénario ni workflow ne l'appelle encore
   (le webhook en erreur remonte dans l'historique du hook), puis **supprimer**.

Couper avant de supprimer : la suppression d'un scénario Make est définitive, et le
webhook `1997221` (*Attio - Nouvelle Note Enrichie*) part avec.

## 2. Couper le déclencheur côté Attio

C'est ce qui envoie les données au webhook — et c'est le « bouton » que les commerciaux
devaient cliquer.

1. Attio → **Workspace settings** → **Automations / Workflows**.
2. Chercher l'automatisation qui envoie une requête vers le webhook Make
   `hook.eu1.make.com/npb1ds…` (hook id `1997221`, nom *Attio - Nouvelle Note Enrichie*).
   L'URL complète se lit dans Make, sur le module 1 de l'ancien scénario.
3. La désactiver, puis la supprimer.
4. Si un bouton / une action manuelle est exposé sur l'objet *Deals* pour la lancer,
   le retirer aussi : sinon les commerciaux continueront de cliquer sur un bouton mort.

## 3. Nettoyer les notes déjà écrites

Deux titres ont été produits par l'ancien scénario, sur l'objet **Deals** :

- `Note enrichie par IA` (jusqu'à mi-août 2026)
- `Informations clés du client` (depuis le 27/08/2026)

Elles sont toutes vides de contenu utile. Pour les supprimer :

1. Attio → **Notes**, filtrer sur le titre, trier par date.
2. Sélection multiple → **Delete**.

Il n'existe pas d'API publique de suppression de notes exposée par l'intégration Make :
c'est un nettoyage manuel, ou un script utilisant la clé API Attio
(`DELETE /v2/notes/{note_id}`).

⚠️ Ne supprimez que ces deux titres. Les notes `Note de CR RDV`,
`Qualification du lead`, `Appel répondu`, `BRIEF`, etc. viennent d'autres scénarios
et sont utilisées.

## 4. Scénarios voisins — à ne PAS couper

Ces scénarios contiennent aussi de l'IA et des notes, mais répondent à d'autres besoins :

| Scénario | ID | Statut |
|---|---|---|
| `[PRD] [Attio] CSM - Note IA sur historique entreprise / CRM` | `4663621` | à garder — note CSM hebdomadaire sur les suivis client |
| `[PRD] [Attio] Tool - génération note lors de requalification` | `3548823` | à garder — se déclenche sur une requalification, pas sur une création |
| `[TEST GASPARD] Attio Tool - génération note requalification` | `6934759` | scénario de test — à supprimer si plus utilisé, indépendamment de ce chantier |
