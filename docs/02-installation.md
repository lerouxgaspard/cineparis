# Installation du scénario

Compter 5 à 10 minutes. Organisation Make : `Morning (bidule@morning.fr)` (id `22947`),
équipe `Morning` (id `16139`).

## 1. Importer le blueprint

1. Make → **Scenarios** → **Create a new scenario**.
2. Menu `⋯` en bas → **Import Blueprint**.
3. Charger `make/brief-ia-nouveau-deal.blueprint.json`.

Le scénario apparaît avec ses 11 modules et le nom
`[PRD] [Attio] Brief IA - Nouveau Deal (auto)`.

## 2. Vérifier les connexions

| Module | App | Connexion pré-remplie |
|---|---|---|
| 1, 3, 4, 5, 11 | Attio | `Morning - New Prod` (id `3292919`) — celle déjà utilisée par les scénarios PRD |
| 8 | Anthropic Claude | `Morgane - BYM Classification` (id `8495429`) |

⚠️ **Le module 8 est à revoir.** Les quatre connexions Anthropic de l'équipe sont soit
nommées « ne pas utiliser », soit rattachées à un autre usage. Créez une connexion
Anthropic dédiée production (clé API du compte Morning) et sélectionnez-la sur le
module 8 avant d'activer.

## 3. Régler la planification

Le format d'export Make ne transporte pas la planification : elle est à régler à la main.

- Ouvrir le panneau **Scheduling** (l'horloge en bas à gauche).
- **Run scenario** : `At regular intervals` → **5 minutes**.

Le module 1 va chercher les deals créés dans les **30 dernières minutes** : la fenêtre
recouvre largement l'intervalle, donc un retard ou une exécution ratée ne fait rien
perdre. Les recouvrements ne créent pas de doublons (voir étape 5).

Si vous changez l'intervalle, gardez une fenêtre au moins 3× plus large que
l'intervalle. La fenêtre se règle dans le module 1 (`addMinutes(now; -30)`).

## 4. Faire un « Run once » avant d'activer

**Ne pas activer directement.** Cliquez sur **Run once** et vérifiez, module par module :

| Module | À vérifier |
|---|---|
| 1 – Deals créés | La réponse contient bien `body.data` (0 deal est un résultat valide : relancez à un moment où un deal vient d'être créé, ou élargissez temporairement `addMinutes(now; -30)` à `-1440`) |
| 3 – Notes déjà présentes | Statut 200 |
| 4 – Contact | `body.data` contient le contact, ou une liste vide si le deal n'a pas de contact |
| 8 – Claude | Statut 200, et `body.content` contient plusieurs blocs (`server_tool_use`, `web_search_tool_result`, `text`) |
| 9 – Texte du brief | La variable `BRIEF` contient du texte lisible, pas `[À compléter]` |
| 11 – Note | Statut 200, et la note apparaît sur le deal dans Attio |

Puis relisez la note dans Attio. C'est le seul test qui compte.

## 5. Ce que le scénario garantit

- **Pas de doublon** : le module 3 liste les notes du deal et le filtre du module 4 arrête
  le traitement si un titre contient déjà `Brief IA`.
- **Pas de note vide** : le filtre du module 11 exige un brief de plus de 80 caractères.
- **Pas d'erreur sur un deal incomplet** : les modules 4 et 5 utilisent
  `POST .../records/query` avec un filtre sur `record_id` plutôt qu'un `GET` par id —
  un identifiant vide renvoie une liste vide (200) au lieu d'un 404.
- **Deals sans entreprise ni contact ignorés** : le filtre du module 4 exige au moins l'un
  des deux. Un deal sans rien à rechercher ne consomme pas d'appel au modèle.

## 6. Activer

Bascule **ON**. Puis, pendant 24 h, surveillez l'onglet **History** : les exécutions à
0 opération utile (aucun deal dans la fenêtre) sont normales et coûtent 1 opération.

## En cas de timeout sur le module 8

Si le module 8 tombe en erreur `Connection timeout`, l'appel Claude dépasse le délai
autorisé par l'app Make. Dans l'ordre :

1. Réduire `max_uses` de l'outil `web_search` de `5` à `3` dans le corps du module 8.
2. Si ça ne suffit pas, remplacer le module 8 par le module **HTTP → Make a request**,
   qui expose un réglage **Timeout** (jusqu'à 300 s) :
   - URL `https://api.anthropic.com/v1/messages`, méthode `POST`
   - En-têtes : `x-api-key` (la clé Anthropic, à stocker dans les **Keys** de Make),
     `anthropic-version: 2023-06-01`, `content-type: application/json`
   - Corps : identique, copié depuis le module 8
   - Adapter la référence `8.body.content` du module 9 au nouvel identifiant de module.
