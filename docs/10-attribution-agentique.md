# Attribution agentique des leads « À la journée »

> **En production depuis le 08/09/2026 09:55.** Scénario `7299000`
> (`[PRD] [Attio] Attribution agentique - À la journée`), branché sur le webhook
> historique `[DEV][JOURNEE_V3.1]` (hook `3456539`). L'ancien scénario `6720662` est
> désactivé et son blueprint archivé dans `make/legacy-6720662.blueprint.json`.
>
> Première application réelle de la règle, à 09:56 : le lead *SDR// Acne Studios*
> (15 000 €) est parti chez Jules au lieu de la rotation. Le lead précédent, traité
> à 09:29 par l'ancien scénario, était parti en round robin avec un `score_prioritaire`
> calculé puis ignoré.

Remplace le scénario `[DEV] À la journée - Round Robin - Attribution + Valeur + Slack - Gaspard`
(id `6720662`), dont la règle d'attribution n'a jamais existé.

## 1. Pourquoi l'ancien scénario ne marche pas

Diagnostic établi en lisant le blueprint complet des 14 modules.

| # | Constat | Preuve |
|---|---|---|
| 1 | **La règle du PDF n'est pas implémentée.** Aucun routeur, aucun filtre dans tout le blueprint. | `grep '"filter"\|"routes"'` → 0 occurrence |
| 2 | **Le scoring ne décide rien.** `valeur_score` + `urgence_score` + `recurrence_score` → `total_score`, écrit dans Attio (`score_prioritaire`), jamais relu pour choisir. | module 14 : `assignee_id = {{6.rr_id}}`, `attribution_mode = "Round-robin"` en dur |
| 3 | **Toutes les tâches Attio pointent sur le même deal.** | module 8 : `"target_record_id": "a78d3b55-a3e6-4811-9c42-d2a32ef62438"` |
| 4 | **IML invalide dans le message Slack.** | `{{ifempty(1.date_start; \ + "À préciser")}}` — le `\ +` n'est pas de la syntaxe Make |
| 5 | **`deal_value` recalcule un prix** (72 €/pax/jour SDR, 55 € bureau, plancher 4 pax) au lieu de lire la valeur saisie. | module 6 |

Conséquence : le scénario fait **toujours** du round robin, quel que soit le montant du deal.

## 2. Ce que fait le nouveau dispositif

L'agent **lit**, la règle **décide**. Le module `ai-local-agent:RunLocalAIAgent` n'a qu'un
seul travail : analyser le texte libre des notes et dire si le besoin est récurrent. Le choix
du commercial reste déterministe, donc rejouable et auditable.

### Scénario 1 — Attribution (webhook)

```
Webhook
 → Attio GET deal
 → Attio GET notes           [filtre : ni « Coworking à la journée », ni Automation Stop]
 → Airtable Search (pool Equipe_Daily, tri dernier_lead_daily ASC)
 → Array aggregator
 → AGENT (Make AI Provider)  → { recurrence_detected, recurrence_frequency,
                                 valeur_estimee, confiance, justification }
 → Set variables (normalisation)
 → If-Else
     ├─ valeur > 5000 € OU récurrent  → Jules
     └─ sinon                          → premier du round robin
 → Merge → Get variables
 → Attio PATCH (owner, recurrence_detected, value)
 → Airtable Update (dernier_lead_daily = now)
 → Slack DM au commercial
 → Attio POST tâche « Nouveau deal entrant - Call prise de brief »
 → Slack post #100sdr   [error handler: Ignore]
 → Webhook respond
```

**Jules reste dans le round robin.** Le PDF disait de l'en exclure ; la consigne retenue est
l'inverse. L'équilibre se fait tout seul : `dernier_lead_daily` est mis à jour pour l'assigné
*quel qu'il soit*, donc un lead prioritaire attribué à Jules le renvoie en fin de file.

### Scénario 2 — Escalade (planifié toutes les 5 min)

```
Attio POST /records/query   [stage = Contact Entrant
                             ET PAS (escalade_envoyee = true)
                             ET created_at < now - 15 min
                             ET created_at > now - 4 h]
 → Airtable Equipe_Daily → Array aggregator     (traduire les UUID en noms)
 → Iterator sur les leads → Array aggregator    (une ligne par lead)
 → Slack SearchUser (Jules)  [filtre : length(digest) > 0]
 → Slack DM — UN SEUL message listant tous les leads
 → Iterator sur le digest → Attio PATCH escalade_envoyee = true
```

**Pourquoi un digest et non un DM par lead.** Mesuré le 08/09 sur quatre heures de
données réelles : six leads étaient restés au stage Contact Entrant. La règle des
5 minutes n'est presque jamais tenue, donc un DM par lead aurait donné une vingtaine
de notifications par jour à une seule personne — coupées en vingt-quatre heures, et
l'escalade n'aurait plus rien escaladé. Un message par passage reste lisible.

**Le marquage vient après la notification.** Si Slack tombe, les leads ne sont pas
marqués et seront repris au passage suivant. L'inverse aurait perdu l'alerte
définitivement.

**Le propriétaire est résolu en nom.** L'API Attio ne renvoie qu'un UUID de
workspace-member ; la table `Equipe_Daily` sert de trombinoscope, en une seule
requête par passage et non une par lead.

Deux subtilités du filtre, l'une et l'autre vérifiées contre les données réelles :

- **`$not … $eq true`, et non `$eq false`.** L'attribut `escalade_envoyee` vient d'être
  créé : il est *absent* de tous les deals existants, et `null` n'est pas `false`. La forme
  négative attrape les deux.
- **La borne basse à 4 heures est indispensable.** Plus de 50 deals (`has_more: true`) sont
  au stage Contact Entrant depuis le 2 septembre. Sans elle, le premier run envoyait 50 DM
  à Jules d'un coup, puis 50 de plus toutes les 5 minutes. Au-delà de quelques heures, un
  lead resté à Contact Entrant n'est plus un SLA raté à signaler — c'est du nettoyage de
  pipe, qui ne relève pas de ce scénario.

Pourquoi un second scénario : **`util:FunctionSleep` est plafonné à 300 secondes** (vérifié
sur le schéma du module). Un délai de 15 minutes en ligne est impossible, et bloquer un run
webhook 15 minutes empilerait les exécutions.

## 3. Identifiants relevés sur l'instance

| Ressource | Valeur |
|---|---|
| Organisation / équipe Make | `22947` / `16139` (zone `eu1.make.com`) |
| Connexion Attio | `3292919` — Morning - New Prod |
| Connexion Airtable | `2426866` |
| Connexion Slack | `53760` — Robot Bidule |
| Connexion Make AI Provider | `9767251` |
| Objet Attio | `deals_daily` (`daa76d55-3f01-40f7-88ee-4e5f39f7d524`) |
| Jules Bornhauser | `e1ddf2ca-504e-4510-b53d-1d7fb16d9f96` |
| Base / table Airtable | `app1ZLIN13lGG0cPE` / `tbl362A2eveuwpuBE` (Equipe_Daily) |
| Champ `dernier_lead_daily` | `fldmq0SDLFYe3gJoS` |
| Modèle de l'agent | `defaultModel: "large"` (Make AI Provider → gpt-5-mini) |
| Canal Slack | `#100sdr` → `C084VQ7D6B0` |

### Écarts entre le PDF et la réalité Attio

- Le stage **« Lead entrant » n'existe pas**. Les stages réels : `Contact Entrant`,
  `Lead Qualifié`, `Proposal`, `Proposal / Recurring`, `Won`, `Lost`. L'escalade filtre
  sur **Contact Entrant**.
- Le canal **`#100journées` n'existe pas**. Deux candidats : `#100àlajournée`
  (`C0ARC9N68F2`, 2 membres, sans le bot ni Jules) et `#100sdr` (`C084VQ7D6B0`,
  24 membres dont Robot Bidule et Jules, déjà utilisé par l'ancien scénario).
  **Retenu : `#100sdr`** — c'est là que se trouvent les commerciaux.
- Le champ « Besoin récurrent détecté » **existe déjà** : `recurrence_detected` (checkbox).
  L'agent n'a qu'à le cocher.

## 4. Avant d'importer

1. ~~Créer la checkbox `escalade_envoyee`~~ — **fait**, vérifié via le connecteur :
   `d84fdbbb-7e6b-4a0c-8e3d-6f85de9dfa4b`, slug `escalade_envoyee`, type checkbox,
   écrivable, non requis.
2. Rien à faire côté Slack : **Robot Bidule est déjà membre de `#100sdr`**, avec les
   24 personnes concernées. C'est ce qui a motivé le choix de ce canal plutôt que
   `#100àlajournée`, qui n'avait ni le bot, ni Jules, ni aucun commercial.

### Ordre des notifications et tolérance aux pannes

Le DM au commercial et la tâche Attio passent **avant** le post canal, et seul le post
canal porte un handler `Ignore`. Raison : au premier run, l'échec Slack sur le canal a
interrompu le scénario alors que le deal était déjà assigné (module 13) et la rotation
déjà consommée (module 14) — le lead s'est retrouvé attribué, sans tâche et sans réponse
webhook. Le DM et la tâche sont le coeur du dispositif et doivent échouer bruyamment ;
la diffusion sur le canal est du confort et ne doit plus rien bloquer.

## 5. Import

Pour chaque scénario : Make → *Create a new scenario* → menu `···` → *Import Blueprint* →
coller le JSON.

| Fichier | Scénario |
|---|---|
| `make/attribution-agentique.blueprint.json` | Attribution (webhook) |
| `make/escalade-5min.blueprint.json` + `make/escalade-5min.scheduling.json` | Escalade (toutes les 5 min) |

Puis, à la main dans l'éditeur :

- **Scénario 1** : recréer le webhook (le blueprint ne peut pas le porter — règle Make).
  Le **modèle de l'agent est désormais pré-rempli** : `defaultModel: "large"`, relevé sur
  le scénario 7299000 après réglage manuel. Côté Make AI Provider, « Large » correspond à
  `gpt-5-mini`, reasoning low, réservé aux plans payants. Le RPC `RpcGetModels` reste
  refusé hors contexte organisation, donc cette valeur n'est pas redécouvrable : elle est
  codée dans le générateur. Sans elle, l'import échoue sur
  `config.llmConfig.llmModel Required`.
- **Scénario 2** : régler la planification sur 5 minutes.

## 6. État de validation

| Vérification | Résultat |
|---|---|
| `validate_blueprint_schema` (scénario 1) | valide |
| `validate_blueprint_schema` (scénario 2) | valide |
| `validate_scheduling_schema` | valide |
| `validate_module_configuration` — Attio, Airtable ×2, Slack ×2, SetVariables, GetVariables, BasicFeeder | valides |
| `validate_module_configuration` — module Agent | **non vérifiable** : `RpcGetModels` refusé hors contexte organisation |

Trois erreurs réelles ont été corrigées grâce à ces validations :
`util:GetVariables` attend `variables` et non `names` ; `maxRecords` doit être un nombre
et non une chaîne ; et le module Sleep ne peut pas dépasser 300 s.

Le scénario d'attribution tourne désormais sur du trafic réel : la forme des réponses
Attio (`values.<champ>[]`) est confirmée, tout comme le module Agent et la décision.

Le scénario d'escalade (`7299041`), lui, **n'a jamais été exécuté** — à vérifier avant
de l'activer : planification sur 5 minutes, et un premier passage à blanc pour contrôler
la syntaxe du filtre Attio (`$not`, bornes `created_at`).

### Reste à faire

- Arbitrer `dans_rotation` (voir §7).
- Supprimer les webhooks devenus orphelins : `[DEV][JOURNEE_V3]` (`3456305`). Quatre hooks
  aux noms voisins ont déjà causé une erreur de branchement lors de la bascule.

## 7. Le piège `dans_rotation`

La table `Equipe_Daily` porte deux cases distinctes, et elles ne disent pas la même chose :

| Personne | `actif` | `dans_rotation` |
|---|---|---|
| Jules Bornhauser | ✅ | ❌ |
| Justine, Juliette, Paul | ✅ | ✅ |
| Vincent Bergerot, Louise Pauriol | ❌ | ✅ |

La formule du module 4 ne filtre que sur `actif` (et l'absence). Le pool fait donc
4 personnes, **Jules compris** — conforme à la consigne retenue, qui contredit le PDF.

`dans_rotation` est décoché pour Jules et lui seul : c'est l'ancienne règle « exclure Jules
du Round Robin » figée dans la donnée. Le scénario l'ignore volontairement. Tant que cet
écart subsiste, quiconque « corrigera » la formule pour honorer `dans_rotation` inversera
la décision sans s'en apercevoir. À arbitrer : cocher `dans_rotation` pour Jules, ou
supprimer le champ — Vincent et Louise l'ont coché mais sont de toute façon écartés
par `actif`.
