# Correctifs à appliquer à la main dans Make

Le connecteur Make disponible ici est en **lecture seule** sur les scénarios (pas d'écriture
de blueprint), donc ces 3 modifications doivent être faites dans l'éditeur Make.
Elles sont toutes des remplacements d'expression, sans ajout ni suppression de module.

---

## 1. Scénario 5486620 — prix du bistronomique

**`[DEV] OPS + EVENTS – Create task (plateaux repas) from FILLOUT to ASANA - Aurélien`**
→ module **8**, *Set variable* `menu_price`

Avant :

```
{{switch(1.answers.`9UXy`; "Le méditerranéen"; 25; "La cuisine du marché"; 35; "Le bistronomique"; 45; "Le repas de chef"; 50)}}
```

Après :

```
{{switch(1.answers.`9UXy`; "Le méditerranéen"; 25; "La cuisine du marché"; 35; "Le bistronomique"; 40; "Le repas de chef"; 50)}}
```

Seul `45` → `40` change.

---

## 2. Scénario 5518932 — libellés de gammes obsolètes

**`[PRD] OPS + EVENTS – Notify client D-1 (plateaux repas) - Aurélien`**
→ module **7**, *Set multiple variables*, variable `menu_price`

Avant (anciens noms de gammes, plus jamais rencontrés → variable vide) :

```
{{switch(3.fldBNJUaCQc6n9cKd; "Essentielle"; 25; "Équilibre"; 35; "Raffinée"; 45; "Signature"; 50)}}
```

Après :

```
{{switch(3.fldBNJUaCQc6n9cKd; "Le méditerranéen"; 25; "La cuisine du marché"; 35; "Le bistronomique"; 40; "Le repas de chef"; 50)}}
```

Dans l'éditeur, `3.fldBNJUaCQc6n9cKd` s'affiche comme la pastille **Gamme** du module
*Get record* ; ne pas la retaper, seuls les libellés et les prix changent.

---

## 3. Scénario 5518932 — mauvais champ dans le montant total

**Même scénario** → module **2** (*Gmail – Send an email*), bloc HTML, ligne « Montant total »
(juste après les 3 lignes de menus, avant la section « Modalités de commande »).

Avant :

```
{{((3.fldyb794vL3b3CKex + 3.fldAlIfo3ygrvV6AH + 3.fld7AhKYd20IEl5vT) * parseNumber(7.menu_price; ","))}}€ HT
```

Après :

```
{{((3.fldyb794vL3b3CKex + 3.fldAlIfo3ygrvV6AH + 3.fld8HoxBzT5PU1f4s) * parseNumber(7.menu_price; ","))}}€ HT
```

Dans l'éditeur les pastilles portent leur libellé, donc concrètement :

| | Pastille affichée |
|---|---|
| à retirer | **Intolérances menu viande** (`fld7AhKYd20IEl5vT`) |
| à mettre  | **Nombre de menu viande** (`fld8HoxBzT5PU1f4s`) |

C'est exactement la pastille déjà utilisée deux lignes plus haut, dans la ligne « Menu viande ».

---

## Vérification

Le plus simple est de relancer le scénario 5518932 en mode *Run once* et de pousser
manuellement un `recordId` de test sur le webhook :

```
POST https://hook.eu1.make.com/xxha88icn24dtm1tm9kv7lfl32u2nh0h
Content-Type: application/json

{"recordId": "recwPHcxG7bX1hSiL"}
```

`recwPHcxG7bX1hSiL` = commande Charlotte Marchand, gamme **Le bistronomique**, livraison passée
(30/07). Le mail doit afficher `40€ HT` par menu et un total cohérent.

⚠️ Ce record a une vraie adresse client dans le champ `Email` : avant le test, remplacer
temporairement le destinataire du module Gmail par ta propre adresse, ou utiliser un record
de test à toi. Le scénario recoche aussi `Mail J-1` en fin de course (déjà coché ici, donc
sans effet).
