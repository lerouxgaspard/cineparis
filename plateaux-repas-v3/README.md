# V3 tech — Plateaux repas (Le Club)

Diagnostic technique des 4 sous-tâches de [V3 tech](https://app.asana.com/1/40297021214942/task/1218057167204961),
elle-même sous [V3_plateaux repas_le club](https://app.asana.com/1/40297021214942/task/1216817904983388).

Rien n'a encore été modifié en production : ce document établit la cause racine de chaque
point et le correctif exact à appliquer.

## Comment marche la chaîne aujourd'hui

**Commande (temps réel)**

```
Formulaire Fillout
  └─> Make 5486620 « [DEV] OPS + EVENTS – Create task (plateaux repas) from FILLOUT to ASANA »
        ├─ Airtable  Le Club / Plateaux repas   (search + update de la ligne créée par Fillout)
        ├─ Airtable  Le Club / Espaces          (récupère MM, projet Asana, mail génerique)
        ├─ variable  menu_price = switch(gamme)
        ├─ Gmail     mail de confirmation au client (club@morning.fr)
        ├─ Airtable  RH / Collaborateurs        (référent event -> assigné Asana)
        └─ Asana     création de la tâche + champ « tag accueil »
```

Le scénario s'appelle `[DEV]` mais c'est bien lui qui tourne (`isActive: true`).
`7201661 [TEST] … (copy)` est une copie inactive, identique module pour module.

**Rappel J-1 (censé partir la veille)**

```
Airtable  Le Club / Plateaux repas
  vue « // Mail J-1 » (viwXcjoVe4a4pC9YQ)
  └─> Automation « Automation 1 » (wflqOCNnIjoemKjic), déclencheur « quand un enregistrement
      entre dans la vue », script -> POST hook.eu1.make.com/xxha88…
        └─> Make 5518932 « [PRD] OPS + EVENTS – Notify client D-1 (plateaux repas) »
              ├─ Airtable  get Plateaux repas + get Espaces
              ├─ variable  menu_price = switch(gamme)
              ├─ Gmail     mail « Rappel - Votre plateau repas pour demain »
              └─ Airtable  coche « Mail J-1 » (anti-doublon)
```

---

## 1. Rappel client envoyé trop tôt (J-2) — **cause trouvée**

Le déclencheur est l'entrée dans la vue `// Mail J-1`, qui s'appuie sur le champ formule
**« Date dans : »** (`fldioRM7aMa6wmyFE`) :

```
DATETIME_DIFF(
  DATETIME_PARSE({Date souhaité}, 'DD/MM/YYYY - HH:mm'),
  NOW(),
  'days'
)
```

`DATETIME_DIFF(…, 'days')` renvoie un **écart en heures tronqué**, pas un écart de jours
calendaires. Le champ vaut donc `1` pendant les **24 h qui vont de J-2 (heure de livraison)
à J-1 (heure de livraison)** — et pas pendant la journée J-1.

Concrètement : livraison le vendredi à 12 h 15 → dès le **mercredi 12 h 20** l'écart passe
sous 2,0 et le champ affiche `1`, l'enregistrement entre dans la vue, le mail part. Soit J-2.

**Preuve sur la commande réelle de Francis Aguey** (`recx9D7RzTT6Ud1nU`) :

| | |
|---|---|
| Date souhaitée | 12/08/2026 - 11:45 |
| Exécution Make 5518932 | 10/08/2026 12:01 UTC (14 h 01 Paris) |
| Écart réel | 1,99 jour → tronqué à `1` |

Le mail est parti le **10 août** pour une livraison le **12 août**. C'est bien le J-2 signalé
par la cliente, et ce n'est pas un cas isolé : ça se produit pour **toute** commande dont
l'heure de livraison est en journée.

### Correctif minimal — comparer des jours calendaires

`{Date souhaité}` est au format `DD/MM/YYYY - HH:mm`, donc ses 10 premiers caractères sont
la date. Nouvelle formule pour « Date dans : » :

```
DATETIME_DIFF(
  DATETIME_PARSE(LEFT({Date souhaité}, 10), 'DD/MM/YYYY'),
  DATETIME_PARSE(DATETIME_FORMAT(SET_TIMEZONE(NOW(), 'Europe/Paris'), 'YYYY-MM-DD'), 'YYYY-MM-DD'),
  'days'
)
```

Le champ vaut alors exactement `1` **toute la journée de la veille**, et jamais avant.
La vue et l'automation n'ont pas besoin de bouger.

Effet de bord à connaître : `NOW()` se rafraîchit toutes les ~15 min, donc le mail partira
peu après **minuit** le jour J-1.

### Correctif recommandé — envoyer à heure fixe

Si on veut maîtriser l'heure d'envoi (9 h par exemple), il faut sortir du déclencheur
« entrée dans une vue », qui n'est par nature pas pilotable dans le temps :

1. automation Airtable **planifiée** à 9 h, tous les jours ;
2. action *Find records* sur `Plateaux repas` : `Date souhaité` = demain **et** `Mail J-1` décoché ;
3. boucle sur les résultats → le script POST existant, inchangé.

Make 5518932 n'a alors rien à changer non plus, et on gagne au passage la robustesse :
une commande passée à J-1 (donc jamais « entrée » dans la vue au bon moment) est rattrapée
le lendemain matin.

---

## 2. Prix du menu bistronomique à 40 € HT

Le prix est écrit **à trois endroits** ; la sous-tâche est cochée mais deux d'entre eux
sont encore à corriger.

| Endroit | Valeur actuelle | Rôle |
|---|---|---|
| Formulaire Fillout, calcul `u4X1` | à vérifier côté Fillout | montant total facturé, repris tel quel dans le mail de confirmation |
| Make **5486620**, module 8 `menu_price` | `Le bistronomique; 45` | prix ligne à ligne du mail de confirmation |
| Make **5518932**, module 7 `menu_price` | **gammes obsolètes** (voir ci-dessous) | prix ligne à ligne + total du mail de rappel |

Expression actuelle dans 5486620 (module 8) :

```
switch(1.answers.`9UXy`; "Le méditerranéen"; 25; "La cuisine du marché"; 35; "Le bistronomique"; 45; "Le repas de chef"; 50)
```

→ remplacer `45` par `40`.

### Bug bloquant découvert au passage : le mail de rappel n'affiche plus aucun prix

Le `switch` du scénario de rappel (5518932, module 7) référence les **anciens noms de gammes** :

```
switch(3.fldBNJUaCQc6n9cKd; "Essentielle"; 25; "Équilibre"; 35; "Raffinée"; 45; "Signature"; 50)
```

Or le champ `Gamme` de Airtable ne propose plus que : *Le méditerranéen*, *La cuisine du marché*,
*Le bistronomique*, *Le repas de chef*. Vérifié sur les 17 commandes de la table : **aucune**
n'utilise plus les anciens libellés. `menu_price` est donc **vide** depuis le renommage,
et les montants du mail de rappel sont faux ou vides.

À remplacer par les libellés actuels, avec les mêmes prix que 5486620 :

```
switch(3.fldBNJUaCQc6n9cKd; "Le méditerranéen"; 25; "La cuisine du marché"; 35; "Le bistronomique"; 40; "Le repas de chef"; 50)
```

### Deuxième bug dans le même mail : mauvais champ dans le total

Toujours dans 5518932, le montant total est calculé ainsi :

```
((3.fldyb794vL3b3CKex + 3.fldAlIfo3ygrvV6AH + 3.fld7AhKYd20IEl5vT) * parseNumber(7.menu_price; ","))
```

- `fldyb794vL3b3CKex` = Nombre de menu végétarien ✅
- `fldAlIfo3ygrvV6AH` = Nombre de menu poisson ✅
- `fld7AhKYd20IEl5vT` = **Intolérances menu viande** (texte) ❌

Le bon champ est `fld8HoxBzT5PU1f4s` (*Nombre de menu viande*), celui déjà utilisé deux lignes
plus haut pour la ligne « Menu viande ». En l'état, le total ignore les menus viande et
concatène un texte libre.

Pour fiabiliser durablement, l'option propre est de faire porter le prix par Airtable
(un champ `Prix HT` sur une table `Gammes`, ou un champ formule sur `Plateaux repas`) et de
supprimer les deux `switch` : un seul endroit à mettre à jour au prochain changement de tarif.

---

## 3. Ajouter tous les MM de l'espace en collaborateurs — **c'est la donnée, pas le code**

Le scénario gère déjà N Morning Managers. Module 7 (Asana → Create task) :

```
followers: {{split(replace(4.fldUG6WJQBBg093wE; space; emptystring); ",")}}
```

`fldUG6WJQBBg093wE` = champ texte **« Asana_User ID »** de `Le Club / Espaces`, saisi à la main.
Quand il contient plusieurs ID séparés par des virgules, tous sont ajoutés — vérifié sur des
tâches réelles :

- *Le Club - Plateaux repas - Krème - Laffitte* → Cloé, Lila, Rania (3 MM, 3 ID dans Airtable) ✅
- *… - Blue Yonder France SAS - Argentine* → Alexis, Soraya (2 MM, 2 ID) ✅
- *… - CYTOKINETICS - Boulogne* → Clémence seule, car Airtable ne contient qu'un ID

Le problème est donc la **complétude du champ**. Écarts relevés sur les 52 espaces :

| Espace | « Asana_User ID » | « Email (from Morning Managers) » |
|---|---|---|
| Saint-Augustin | 1 ID | 2 emails (elsa.ortiz, antoine.scognamiglio) |
| Laffitte | 3 ID | 4 emails (Adrien AILLAUD n'a pas d'ID Asana renseigné en RH) |
| Cadet | **vide** | 1 email |

Et dans l'autre sens, des MM actifs de la base RH (`appy0jxTXyBp3DOA9` / `tblHR1vvi31QXZ90W`,
rôle « MM » + statut Actif, 58 personnes) n'apparaissent dans aucun espace côté Le Club :
Charlotte DENIZET, Nicoletta MEGOULAS RONCIN, Daphné FENAUX.

Les deux champs de `Le Club / Espaces` sont du texte libre saisi à la main, donc ils
divergeront à nouveau à chaque mercato.

**Correctif court terme** : compléter les 3 espaces ci-dessus (+ renseigner l'ID Asana d'Adrien
AILLAUD dans la base RH).

**Correctif durable** : la base RH est déjà la source de vérité (rôle « MM », statut
Actif/Inactif, lien vers l'espace, ID Asana par personne). Deux options :

- remplacer le champ texte par un **lookup** depuis la base RH, si les deux bases peuvent être
  liées (elles sont distinctes aujourd'hui : `appZJKNcoVfvcVB6g` vs `appy0jxTXyBp3DOA9`) ;
- sinon, un petit scénario Make de synchronisation quotidienne RH → `Le Club / Espaces`, qui
  réécrit `Asana_User ID` et `Email (from Morning Managers)` à partir des MM actifs de chaque
  espace. C'est l'option réaliste vu la séparation des bases.

---

## 4. Paiement par carte obligatoire — faisable, mais ça change le process

Techniquement oui : Fillout gère un champ de paiement Stripe, qu'on peut rendre obligatoire
pour valider le formulaire. Ce n'est pas un point technique isolé, ça touche trois choses :

- les mails disent aujourd'hui « Règlement à réception de la facture » (mail de rappel,
  section Paiement) — à réécrire ;
- le champ `Facturation` (`fldkDTNMuuQp65t3M`) de `Plateaux repas` et le circuit de facturation
  associé perdent leur objet pour ces commandes ;
- le montant encaissé serait celui du calcul Fillout `u4X1` au moment de la commande : toute
  modification ultérieure (nombre de couverts, gamme) devient un avoir/complément à gérer à
  la main. Il faut trancher si on encaisse à la commande ou si on pré-autorise.

À arbitrer avec Cachou / la prod avant de toucher au formulaire — ce n'est pas une décision tech.

---

## Récapitulatif des actions

| # | Action | Où | Statut |
|---|---|---|---|
| 1 | Corriger la formule « Date dans : » (jours calendaires) | Airtable `Le Club` / `Plateaux repas` / `fldioRM7aMa6wmyFE` | ✅ fait le 04/09 |
| 1b | (option) Passer l'automation en planifiée à 9 h | Airtable automation `wflqOCNnIjoemKjic` | à arbitrer |
| 2 | `Le bistronomique` : 45 → 40 | Make 5486620, module 8 | à faire à la main |
| 2b | Remettre les libellés de gammes à jour | Make 5518932, module 7 | à faire à la main |
| 2c | Total : `fld7AhKYd20IEl5vT` → `fld8HoxBzT5PU1f4s` | Make 5518932, mail | à faire à la main |
| 2d | Vérifier le calcul `u4X1` côté Fillout | Fillout | hors MCP, à faire à la main |
| 3 | Compléter Saint-Augustin, Laffitte, Cadet | Airtable `Le Club` / `Espaces` | à valider |
| 3b | Synchro RH → Espaces | nouveau scénario Make | à arbitrer |
| 4 | Paiement CB | Fillout + process facturation | décision métier |

---

## Journal

**04/09/2026 — appliqué en production**

- ✅ Formule « Date dans : » (`fldioRM7aMa6wmyFE`) remplacée par une comparaison de jours
  calendaires, et documentée dans la description du champ. Vérifié : Francis Aguey `-22` → `-23`,
  Charlotte Marchand `-35` → `-36`, Camille Gutton reste à `3` (pas de ré-entrée dans la vue,
  donc pas de mail parasite). Sa commande du 07/09 déclenchera le rappel le **dimanche 06/09**.

**Non appliqué — connecteur Make en lecture seule**

Les 3 corrections des scénarios Make sont à passer à la main, expressions exactes dans
[`correctifs-make.md`](correctifs-make.md).
