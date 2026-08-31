# Coûts, volumétrie et limites connues

## Volumétrie

Deals créés dans Attio sur les derniers jours ouvrés d'août 2026 :

| Date | Deals créés |
|---|---|
| 24/08 | 46 |
| 25/08 | 37 |
| 26/08 | 30 |
| 27/08 | 38 |
| 28/08 | 20 |
| 31/08 | 51 |

Soit **~35 à 50 deals par jour ouvré**, de l'ordre de **800 à 1 000 par mois**.

## Opérations Make

| Poste | Calcul | Ops / mois |
|---|---|---|
| Polling (module 1) | 288 exécutions/jour × 30 | ~8 600 |
| Traitement d'un deal | 6 modules après l'itérateur × ~900 deals | ~5 400 |
| **Total** | | **~14 000** |

Le plan Pro de l'organisation est à 800 000 opérations/mois : l'impact est négligeable
(~1,8 %).

Passer le polling à 10 minutes diviserait la première ligne par deux, au prix d'une
latence plus élevée. À 5 minutes, un commercial qui ouvre le deal a le brief dans la
minute qui suit sa prise de café.

## Coût du modèle

Claude Opus 5 : 5 $ / MTok en entrée, 25 $ / MTok en sortie. La recherche web est
facturée 10 $ pour 1 000 recherches.

Par deal, avec `effort: low` et `max_uses: 5` : de l'ordre de 15-20 k tokens en entrée
(le contenu des pages ramenées par la recherche pèse le plus lourd), ~1 k en sortie, et
3 à 5 recherches.

**Estimation : 0,10 à 0,15 $ par deal, soit ~100 à 140 $ par mois** pour 900 deals.

Deux leviers si c'est trop :

- `"model": "claude-sonnet-5"` dans le module 8 → environ 2,5× moins cher, qualité de
  synthèse un cran en dessous sur les entreprises peu documentées.
- Restreindre le périmètre : ajouter une condition sur le filtre du module 4, par exemple
  `{{2.values.value[1].currency_value}}` supérieur à un seuil, ou
  `{{2.values.resource_type[1].option.title}}` égal à `Bureau fermé`. Les deals
  « à la journée » et nomades à quelques centaines d'euros ne justifient pas toujours une
  recherche complète.

Le périmètre livré est **tous les deals créés**, conformément à la demande.

## Limites connues

- **Le scénario n'a jamais été exécuté.** Chaque module a été validé individuellement
  contre l'API Make (`validate_module_configuration`) et la structure du blueprint contre
  `validate_blueprint_schema`, mais aucun « Run once » n'a pu être lancé : la connexion
  Make de la session était en lecture seule. Le premier run est un vrai test.
- **Latence du module 8.** Un appel Claude avec recherche web prend 30 à 90 secondes.
  Si l'app Make Anthropic impose un délai plus court, le module tombera en timeout — la
  parade est décrite en fin de `02-installation.md`. C'est le point le plus incertain de
  l'installation.
- **En-tête `anthropic-beta: server-side-fallback-2026-07-01`** et `"fallbacks": "default"`
  dans le corps : ils font basculer la requête sur un modèle de repli si le modèle refuse
  de répondre, plutôt que de rendre un brief vide. Si le module 8 renvoie une erreur 400
  mentionnant `beta` ou `fallbacks`, retirez l'en-tête **et** la ligne `"fallbacks"` — le
  reste du scénario fonctionne sans.
- **Deals sans entreprise ni contact liés** : ignorés (rien à rechercher). Ils ne
  recevront jamais de brief, même si l'entreprise est renseignée plus tard — le scénario
  ne regarde que les 30 dernières minutes après la création.
- **Fenêtre glissante** : un deal créé pendant une panne Make de plus de 30 minutes
  n'aura pas de brief. Pour rattraper, élargir temporairement `addMinutes(now; -30)` dans
  le module 1 et lancer un « Run once » — le contrôle d'idempotence évite les doublons
  sur les deals déjà traités.
- **Qualité variable selon le prospect.** Une TPE sans site ni presse donnera un brief
  majoritairement « non trouvé ». C'est le comportement voulu : mieux vaut un brief court
  et honnête qu'un gabarit vide présenté comme une analyse.
