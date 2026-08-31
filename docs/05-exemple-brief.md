# Avant / après sur un vrai deal

Deal `caaae52a-0ca5-49d0-8d65-3e5617333db4` — *Market // Clichy - Vitry - Constance de
Grandcourt - 2 poste(s)*, créé le 25/08/2026, source SEO / site.

## Ce que l'ancien scénario a écrit

Note `a1556121-5b59-415c-9b95-aa67996ebd91`, 31/08/2026 :

```
### Informations sur la personne
(À compléter avec une recherche LinkedIn via le prénom, nom et email)
- Poste actuel : [À trouver]
- Ancien(s) poste(s) : [À trouver]
- Expérience : [À trouver]
- Posts LinkedIn récents : [À trouver (ex : partages, articles, réactions)]

### Informations sur l'entreprise (Vitry)
(Sources : Site web, LinkedIn, articles, communiqués de presse)
- Activité : [À trouver (ex : secteur, produits/services)]
- Actualités récentes :
  - Levée de fonds : [À trouver (montant, date, investisseurs)]
  - Partenariats : [À trouver]
- Site web : [À trouver (ex : vitry.com)]
- LinkedIn : [À trouver (lien vers la page entreprise)]

(Pour des résultats précis, partagez le prénom/nom du prospect ou son email
pour une recherche ciblée.)
```

Zéro information. Et Attio connaissait déjà le site (`vitry.com`), le LinkedIn de la
société, l'effectif (51-250) et une description de l'activité — ces champs n'étaient
simplement pas envoyés au modèle.

## Ce que produit le nouveau prompt

Brief obtenu en appliquant le prompt du module 6 aux données CRM réelles de ce deal, avec
recherche web :

```markdown
**L'entreprise**
- Vitry est un fabricant français d'accessoires de manucure et de pédicure (limes,
  pinces, ciseaux, coupe-ongles en acier inoxydable, garantis à vie), fondé en 1795 et
  positionné sur la coutellerie de précision ; la gamme s'est étendue aux soins des
  mains, des pieds et du visage.
- PME d'environ 145 salariés, site industriel au Bignon (Loire-Atlantique), siège à
  Paris — 112 avenue Kléber, 75116. ARR estimé par Attio : 10-50 M$.
- Après 1 M€ investi dans l'outil industriel en 2024, le groupe a engagé 2,6 M€
  supplémentaires (annoncé en mars 2025) pour agrandir ses locaux et renforcer sa
  logistique. Développement international en cours, notamment Dubaï et Golfe.

**Le contact**
- Constance de Grandcourt travaille chez Vitry sur les sujets marketing et digital, avec
  un périmètre international (publications sur le déploiement de la marque à Dubaï et
  dans les pays du Golfe, septembre 2025).
- Ancienneté chez Vitry : non trouvé. Son profil LinkedIn mentionne une expérience
  antérieure dans la distribution beauté (Credo Beauty).

**Ce que ça dit du besoin**
- Fait : le siège est déjà à Paris 16e et l'entreprise investit pour agrandir ses
  installations ; la demande porte sur 2 postes en bureau fermé, donc une petite
  antenne, pas un déménagement de siège.
- Hypothèse : le développement export (Golfe, Amérique du Nord) peut justifier une
  équipe parisienne réduite et flexible, distincte du siège historique — profil type
  d'un besoin en bureau privé court terme.

**3 questions à poser**
- Ces 2 postes viennent-ils s'ajouter au siège de l'avenue Kléber, ou le remplacer ?
- L'équipe concernée travaille-t-elle sur l'export, ou sur le digital / e-commerce ?
- Quelle échéance avez-vous en tête, et êtes-vous engagés sur un bail ailleurs ?

**Sources**
https://www.vitry.com/en
https://www.lejournaldesentreprises.com/article/leader-de-la-pedicure-et-de-la-manucure-le-groupe-vitry-investit-26-millions-deuros-pour-sagrandir-2115102
https://www.linkedin.com/in/constance-de-grandcourt-085471a3/
https://www.linkedin.com/posts/constancedeg_vitry-in-duba%C3%AF-gulf-arab-states-activity-7375127887101992960-A9OF
```

## Ce qu'il faut regarder dans cet exemple

- **« non trouvé » apparaît vraiment** (ancienneté du contact) au lieu d'un `[À trouver]`.
  C'est le comportement attendu ; une note truffée de « non trouvé » signale un lead sans
  matière publique, pas un scénario cassé.
- **Fait et hypothèse sont séparés**, ce qui évite au commercial d'arriver en visite avec
  une intuition du modèle présentée comme un fait.
- **Les sources sont vérifiables** en un clic.
- **Le brief tient en un écran** : s'il faut le lire pendant qu'on marche vers la salle,
  il doit tenir en 30 secondes.

Ce brief a été produit hors Make, en appliquant le prompt aux mêmes données, pour
valider la qualité de sortie avant l'import. Le premier « Run once » du scénario doit
produire une note de cette forme.
