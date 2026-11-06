# Contrat d'Interface DEV ⇄ DATA — SAÉ 3.01 (Climat & Cultures)

**Version :** 1.1
**Jalon :** Jalon 2 (Semaine 41, mis à jour en S45)
**Format retenu :** JSON ➔ JSON
**Statut :** Validé (conforme au schéma en étoile du datamart et au module `calcul_indicateurs.py`)

### Historique des versions

| Version | Changements |
|---|---|
| 1.0 | Flux entrant DEV ➔ DATA (séries météo et identifiants). |
| 1.1 | Ajout du champ d'entrée optionnel `latitude` (bilan hydrique). Ajout du flux sortant DATA ➔ DEV (section 3), des règles de calcul partagées (section 4) et des erreurs (section 5). Précision : `id_utilisateur` est un entier. |

---

## 1. Objet du document

Ce contrat d'interface fixe le format standard des échanges de données structurées en **JSON** entre le pôle **DEV** (client API Open-Meteo & back-end Flask) et le pôle **DATA** (module de calcul d'indicateurs & alimentation de la base de données).

Le module de calcul est la fonction `calculer_indicateurs(payload)` du fichier `calcul_indicateurs.py` : elle reçoit le JSON de la section 2 sous forme de dictionnaire Python et renvoie le dictionnaire de la section 3.

---

## 2. Flux entrant : séries météo et paramètres (DEV ➔ DATA)

Le pôle DEV transmet au pôle DATA un objet JSON unique contenant le contexte d'analyse ainsi que la série météo journalière.

### 2.1 Spécification de la structure d'entrée

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `id_commune` | `int` | oui | Identifiant interne de la commune, clé étrangère vers `Dim_Commune`. |
| `code_insee` | `string` | non | Code INSEE officiel de la commune (information, non utilisé par le calcul). |
| `id_culture` | `int` | oui | Identifiant de la culture, clé étrangère vers `Dim_Culture`. |
| `id_temps` | `int` | oui | Identifiant de l'horizon temporel, clé étrangère vers `Dim_Temps`. |
| `id_modele` | `int` | oui | Identifiant du modèle climatique, clé étrangère vers `Dim_Modele`. |
| `id_session` | `string` | non | Identifiant de session, pour rattacher les résultats à un visiteur anonyme. |
| `id_utilisateur` | `int` ou `null` | non | Identifiant du compte connecté, clé étrangère vers `Utilisateur`. `null` pour une session anonyme. **Entier, jamais une chaîne.** |
| `latitude` | `float` ou `null` | non | Latitude de la commune en degrés (entre −90 et 90), lue dans `Dim_Commune`. **Nécessaire au bilan hydrique** : sans elle, `bilan_hydrique_mm` vaut `null`. |
| `series` | `array` | oui | Liste non vide des mesures météo quotidiennes (ci-dessous). |

Chaque élément de `series` :

| Champ | Type | Description |
|---|---|---|
| `date` | `string` | Date au format `YYYY-MM-DD`. Unique dans la série. |
| `t_min` | `float` ou `null` | Température minimale du jour, en °C. |
| `t_max` | `float` ou `null` | Température maximale du jour, en °C. |
| `t_moy` | `float` ou `null` | Température moyenne du jour, en °C (transmise par l'API, **non utilisée** par le calcul). |
| `precip` | `float` ou `null` | Cumul quotidien des précipitations, en mm. |

Règles :
- Les températures sont en **°C** et les précipitations en **mm**.
- Une valeur absente de l'API est transmise à `null` : DEV n'invente jamais de valeur.
- La série peut couvrir une ou plusieurs années (un horizon fait environ 10 ans, bornes incluses, soit 11 années civiles).

### 2.2 Exemple de payload entrant

```json
{
  "id_commune": 13,
  "code_insee": "31555",
  "id_culture": 1,
  "id_temps": 2,
  "id_modele": 1,
  "id_session": "sess_8f92a",
  "id_utilisateur": null,
  "latitude": 43.60,
  "series": [
    {
      "date": "2049-05-15",
      "t_min": 8.5,
      "t_max": 22.1,
      "t_moy": 15.3,
      "precip": 4.2
    }
  ]
}
```

---

## 3. Flux sortant : indicateurs calculés (DATA ➔ DEV)

Le module de calcul renvoie un objet JSON unique. Les valeurs de gel, de stress thermique et de GDD sont des **moyennes par an** sur la série reçue (arrondies à 0,1).

### 3.1 Spécification de la structure de sortie

| Champ | Type | Description |
|---|---|---|
| `id_commune`, `id_culture`, `id_temps`, `id_modele` | `int` | Repris à l'identique de l'entrée. |
| `id_session` | `string` ou `null` | Repris de l'entrée (écrit `''` en base si absent). |
| `id_utilisateur` | `int` ou `null` | Repris de l'entrée. |
| `jours_gel` | `float` | Nombre moyen de jours par an où `t_min` est strictement inférieure au `seuil_gel` de la culture. |
| `gdd` | `float` | Cumul moyen annuel de degrés-jours de croissance (méthode plafonnée, base et plafond de la culture). |
| `jours_stress_thermique` | `float` | Nombre moyen de jours par an où `t_max` est supérieure ou égale au `seuil_stress_thermique` de la culture. |
| `bilan_hydrique_mm` | `float` ou `null` | Précipitations moins ET0 (Hargreaves), en mm par an. `null` si `latitude` est absente. |
| `id_verdict` | `int` | Clé vers `Dim_Verdict` : 1 = viable, 2 = menacee, 3 = non_viable. |
| `verdict` | `string` | Libellé : `viable`, `menacee` ou `non_viable`. |
| `nb_annees` | `int` | Nombre d'années retenues dans la moyenne. |
| `nb_annees_incompletes` | `int` | Nombre d'années exclues car trop incomplètes (moins de 90 % des jours attendus). |
| `serie_incomplete` | `bool` | `true` si aucune année n'est complète : le calcul porte alors sur les données disponibles. |
| `nb_jours_ignores` | `int` | Nombre de jours écartés (valeur manquante ou incohérente). |

### 3.2 Exemple de payload sortant

Résultat obtenu sur `sample_data_13.json` (Toulouse, maïs, année 2010, sans latitude) :

```json
{
  "id_commune": 13,
  "id_culture": 1,
  "id_temps": 1,
  "id_modele": 1,
  "id_session": "sample_export_s42",
  "id_utilisateur": null,
  "jours_gel": 20.0,
  "gdd": 3136.9,
  "jours_stress_thermique": 11.0,
  "bilan_hydrique_mm": null,
  "id_verdict": 1,
  "verdict": "viable",
  "nb_annees": 1,
  "nb_annees_incompletes": 0,
  "serie_incomplete": false,
  "nb_jours_ignores": 0
}
```

### 3.3 Écriture en base

Le résultat est écrit dans `Fact_Indicateur` par la fonction `ecrire_fact(conn, resultat)` (requête préparée, `INSERT … ON DUPLICATE KEY UPDATE` sur la contrainte `uq_fait` : commune, culture, horizon, modèle, session). Les séries météo brutes ne sont **jamais** stockées dans le datamart.

---

## 4. Règles de calcul partagées

- **Valeurs manquantes :** un jour dont `t_min` ou `t_max` est `null` (ou `NaN`), ou dont `t_min` est supérieure à `t_max`, est ignoré pour tous les indicateurs. Pour le bilan hydrique, un jour sans `precip` est aussi écarté.
- **Plusieurs années :** chaque année est calculée séparément, puis on fait la moyenne par an. Une année est « complète » à partir de 90 % des jours attendus.
- **Année entière :** par défaut, les indicateurs portent sur l'année entière et non sur la saison de culture (limite assumée, à arbitrer par l'équipe).
- **Seuils :** les paramètres des cultures (base, plafond, seuil de gel, seuil de stress, GDD de maturité) viennent de `Dim_Culture` et doivent rester identiques à `CULTURES` dans `calcul_indicateurs.py` (vérifié par `test_coherence_dim_culture_sql`).
- **Verdict (règle provisoire) :** non viable si le GDD est inférieur au GDD de maturité ; sinon viable jusqu'à 15 jours de stress par an, menacée jusqu'à 30, non viable au-delà.

---

## 5. Erreurs

Le module lève une `ValueError` avec un message explicite dans les cas suivants. DEV doit les attraper et renvoyer une erreur claire (HTTP 400) sans écrire en base.

| Cas | Message |
|---|---|
| Champ obligatoire absent ou `null` | `champ obligatoire manquant : <champ>` |
| Culture inconnue | `id_culture inconnu : <valeur>` |
| `id_utilisateur` non entier | `id_utilisateur doit être un entier ou null, reçu : …` |
| `latitude` hors de [−90, 90] | `latitude hors de [-90, 90] : <valeur>` |
| Série vide | `series vide : impossible de calculer les indicateurs` |
| Date absente, invalide ou en double | `series[i] : date absente ou invalide …` / `date en double …` |
| Température ou précipitation non numérique | `<champ> doit être un nombre ou null, reçu : …` |
| Aucune journée exploitable | `aucun jour exploitable (t_min / t_max absents ou incohérents)` |
