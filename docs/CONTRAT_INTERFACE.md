# Contrat d'Interface DEV ⇄ DATA — SAÉ 3.01 (Climat & Cultures)

**Version :** 1.4
**Jalon :** Jalon 2 (Semaine 41, mis à jour en S45), complété en Jalon 3 (S47) pour l'intégration, puis en Jalon 4 (S49) pour les comptes utilisateurs
**Format retenu :** JSON ➔ JSON
**Statut :** Validé (conforme au schéma en étoile du datamart et au module `calcul_indicateurs.py`). La section 2.3 de la v1.4 a été validée par DATA ; leurs réserves sont reprises en 2.3.

### Historique des versions

| Version | Changements |
|---|---|
| 1.0 | Flux entrant DEV ➔ DATA (séries météo et identifiants). |
| 1.1 | Ajout du champ d'entrée optionnel `latitude` (bilan hydrique). Ajout du flux sortant DATA ➔ DEV (section 3), des règles de calcul partagées (section 4) et des erreurs (section 5). Précision : `id_utilisateur` est un entier. |
| 1.2 | Préparation de l'intégration (J3). `id_session` toujours transmis par DEV, même pour un utilisateur connecté (2.3). Période d'un horizon lue dans `Dim_Temps` et `latitude` lue dans `Dim_Commune` (2.4). Correspondance des variables Open-Meteo → contrat (2.5). Ordre d'appel du module et écriture en base côté DEV (3.4). |
| 1.3 | Décision d'équipe sur la fenêtre de calcul (4.1) : année entière en J3, puis saison de chaque culture à partir de J4 (une période semis → récolte par culture, colonnes `mois_debut` / `mois_fin` dans `Dim_Culture`). Mois à sourcer par DATA. |
| 1.4 | Comptes utilisateurs (J4.1). `id_utilisateur` est renseigné par DEV quand un compte est connecté (2.3). `id_session` est renouvelé à la connexion et à la déconnexion : la session Flask est vidée (2.3). Les calculs faits avant la connexion restent anonymes. |

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
| `id_session` | `string` | oui (côté DEV) | Identifiant de session (`sess_` + uuid), créé à la première visite et rangé dans la session Flask. **Toujours transmis par DEV, y compris pour un utilisateur connecté** (voir 2.3). Le module l'accepte absent, mais DEV ne doit jamais l'omettre. |
| `id_utilisateur` | `int` ou `null` | non | Identifiant du compte connecté, clé étrangère vers `Utilisateur`. `null` pour une session anonyme. **Entier, jamais une chaîne.** |
| `latitude` | `float` ou `null` | oui (côté DEV) | Latitude de la commune en degrés (entre −90 et 90). **Toujours remplie par DEV à partir de `Dim_Commune`** (voir 2.4). **Nécessaire au bilan hydrique** : sans elle, `bilan_hydrique_mm` vaut `null`, sans erreur. |
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
- La série couvre **toutes les années de l'horizon choisi**, en années civiles complètes (un horizon fait environ 10 ans, bornes incluses, soit 11 années civiles). La période exacte est fixée par `Dim_Temps` (voir 2.4).

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

### 2.3 Règle d'identité : `id_session` toujours transmis

DEV envoie **toujours** un `id_session`, que le visiteur soit anonyme ou connecté. `id_utilisateur` s'y ajoute quand un compte est connecté.

| Visiteur | `id_session` | `id_utilisateur` |
|---|---|---|
| Anonyme | `"sess_…"` (obligatoire) | `null` |
| Connecté | `"sess_…"` (obligatoire) | id du compte (`int`) |

**Pourquoi :** la contrainte d'unicité `uq_fait` de `Fact_Indicateur` porte sur commune, culture, horizon, modèle et **session**, mais pas sur l'utilisateur. Si `id_session` manquait, il serait écrit `''` en base. Deux comptes différents faisant la même recherche partageraient alors la même clé, et le second calcul écraserait la ligne du premier, qui resterait au nom du premier compte. Cela casserait l'isolation des données et l'effacement RGPD.

L'identifiant est créé à la première visite (`"sess_" + uuid4().hex`), rangé dans la session Flask (cookie signé avec `SECRET_KEY`) et réutilisé ensuite.

**Renouvellement de `id_session` (v1.4).** La session Flask est vidée à la connexion et à la déconnexion : un nouvel `id_session` est alors créé au prochain calcul. Ainsi, deux comptes qui se succèdent sur le même navigateur ne partagent jamais le même `id_session` (voir « Pourquoi » ci-dessus), et un visiteur qui se connecte ne reprend pas l'identifiant de sa visite anonyme. Les calculs faits avant sa connexion restent donc anonymes (`id_utilisateur = null`) et ne sont pas rattachés à son compte.

**Rattachement au compte (v1.4).** DEV lit l'identifiant du compte connecté (entier, `current_user.id_utilisateur`) et le passe dans le payload à `construire_payload(...)` ; il vaut `null` pour un visiteur anonyme. `calculer_indicateurs` le recopie dans le résultat, et `ecrire_fact` l'écrit dans `Fact_Indicateur.id_utilisateur`. Remarque pour DATA : la clause `ON DUPLICATE KEY UPDATE` de `ecrire_fact` ne modifie pas `id_utilisateur` ; une ligne garde donc le compte qui l'a créée. C'est sans conséquence tant qu'un `id_session` n'est jamais partagé entre deux comptes, ce que garantit le renouvellement ci-dessus. En production, `SECRET_KEY` doit être définie dans les variables d'environnement : avec la valeur par défaut, un cookie de session pourrait être falsifié.

**Réserves de DATA sur la v1.4 (prises en compte).**

1. **`id_session` n'est jamais vide.** DEV le garantit par du code (`construire_payload` refuse un `id_session` vide ou absent, avec une `ValueError`) et par des tests. Une valeur vide serait écrite `''` en base et partagée entre visiteurs.
2. **`id_utilisateur` n'est pas modifié par la clause `ON DUPLICATE KEY UPDATE`** de `ecrire_fact` (vérifié dans `SQL_UPSERT`). Une ligne garde le compte qui l'a créée.
3. **Une ligne par session pour un même compte.** Pour lire le dernier calcul d'un compte, on filtre sur `id_utilisateur` avec `ORDER BY date_calcul DESC, id_fait DESC LIMIT 1`.
4. **Les lignes créées avant la connexion ne sont pas supprimées avec le compte** : elles ont `id_utilisateur = NULL`, donc la suppression en cascade ne les concerne pas. Elles sont purgées comme toute session anonyme (conception RGPD, §5.4). À documenter côté RGPD ; la page « Mon compte » en informe déjà l'utilisateur.

### 2.4 Données lues en base par DEV avant l'appel à l'API

Rien n'est écrit en dur dans le code : DEV lit les dimensions à partir des identifiants choisis par l'utilisateur.

| Donnée | Lue dans | Utilisation |
|---|---|---|
| Période de l'horizon | `Dim_Temps.annee_debut` et `Dim_Temps.annee_fin` | `start_date` = 1er janvier de `annee_debut`, `end_date` = 31 décembre de `annee_fin`. Exemple : horizon 2050 (2040–2050) → `2040-01-01` à `2050-12-31`. |
| Coordonnées | `Dim_Commune.latitude` et `Dim_Commune.longitude` | Paramètres de l'appel Open-Meteo ; la `latitude` est aussi recopiée dans le payload. |
| Modèle climatique | `Dim_Modele.code_api` | Paramètre `models` de l'appel Open-Meteo (un modèle par appel). |

Si DATA modifie les années d'un horizon dans `Dim_Temps`, l'application suit sans changer de code.

### 2.5 Correspondance des variables Open-Meteo → contrat

DEV demande les 4 variables en un seul appel (paramètre `daily`) et renomme les tableaux de la réponse selon cette table. Elle correspond à `CHAMPS_CONTRAT` dans `app/services/openmeteo_client.py`.

| Variable Open-Meteo (`daily`) | Champ du contrat | Unité |
|---|---|---|
| `time` | `date` | `YYYY-MM-DD` |
| `temperature_2m_min` | `t_min` | °C |
| `temperature_2m_max` | `t_max` | °C |
| `temperature_2m_mean` | `t_moy` | °C |
| `precipitation_sum` | `precip` | mm |

Les tableaux de `daily` sont parallèles : l'élément `i` de chaque variable correspond à la date `time[i]`. Une valeur absente ou un tableau trop court donne `null`, jamais `0`.

---

## 3. Flux sortant : indicateurs calculés (DATA ➔ DEV)

Le module de calcul renvoie un objet JSON unique. Les valeurs de gel, de stress thermique et de GDD sont des **moyennes par an** sur la série reçue (arrondies à 0,1).

### 3.1 Spécification de la structure de sortie

| Champ | Type | Description |
|---|---|---|
| `id_commune`, `id_culture`, `id_temps`, `id_modele` | `int` | Repris à l'identique de l'entrée. |
| `id_session` | `string` ou `null` | Repris de l'entrée. Toujours renseigné en pratique (voir 2.3) ; écrit `''` en base seulement s'il manquait. |
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

### 3.4 Ordre d'appel côté DEV (route `/analyse/resultat`)

La route enchaîne toujours les étapes dans cet ordre :

1. **Vérifier les choix** de l'utilisateur (commune, culture, horizon, modèle) en base.
2. **Construire le payload** de la section 2 : `construire_payload(...)` (lecture des dimensions, appel Open-Meteo avec cache, correspondance des variables), avec `id_session` et, si un compte est connecté, son `id_utilisateur`.
3. **Calculer** : `resultat = calculer_indicateurs(payload)`.
4. **Écrire en base** : `ecrire_fact(conn, resultat)`. Uniquement si l'étape 3 a réussi.
5. **Afficher** le résultat à l'utilisateur (indicateurs, verdict, source Open-Meteo et avertissement sur les projections).

En cas d'erreur :

| Étape | Exception | Réaction de DEV |
|---|---|---|
| 1, 2 ou 3 | `ValueError` (entrée invalide) | Message clair et retour au formulaire. Rien n'est écrit en base. |
| 2 | `RuntimeError` (Open-Meteo indisponible, lent ou quota dépassé) | Page de résultat avec un message d'erreur (HTTP 503). Rien n'est écrit. |
| 4 | Erreur de base de données | Erreur enregistrée dans les logs, message générique à l'utilisateur. |

**Connexion à passer à `ecrire_fact` :** l'application utilise Flask-SQLAlchemy, alors que `ecrire_fact` attend une connexion DB-API (requête avec `%s`, `conn.cursor()` et `conn.commit()`). DEV lui passe donc la connexion PyMySQL sous-jacente, et la referme toujours après usage :

```python
conn = db.engine.raw_connection()
try:
    ecrire_fact(conn, resultat)   # fait lui-même le commit
finally:
    conn.close()                  # rend la connexion au pool
```

---

## 4. Règles de calcul partagées

- **Valeurs manquantes :** un jour dont `t_min` ou `t_max` est `null` (ou `NaN`), ou dont `t_min` est supérieure à `t_max`, est ignoré pour tous les indicateurs. Pour le bilan hydrique, un jour sans `precip` est aussi écarté.
- **Plusieurs années :** chaque année est calculée séparément, puis on fait la moyenne par an. Une année est « complète » à partir de 90 % des jours attendus.
- **Fenêtre de calcul :** voir 4.1.
- **Seuils :** les paramètres des cultures (base, plafond, seuil de gel, seuil de stress, GDD de maturité) viennent de `Dim_Culture` et doivent rester identiques à `CULTURES` dans `calcul_indicateurs.py` (vérifié par `test_coherence_dim_culture_sql`).
- **Verdict (règle provisoire) :** non viable si le GDD est inférieur au GDD de maturité ; sinon viable jusqu'à 15 jours de stress par an, menacée jusqu'à 30, non viable au-delà.

### 4.1 Fenêtre de calcul : saison de la culture (décision d'équipe)

Un indicateur n'a de sens agronomique que pendant la période où la culture est en place : le gel de janvier ne menace pas un maïs semé en avril, et la chaleur d'automne n'aide pas une culture déjà récoltée. Les documents du projet le recommandent (note « Logique des indicateurs », §6 : « la fenêtre temporelle compte »).

| Jalon | Règle appliquée |
|---|---|
| **J3 (MVP, actuel)** | **Année entière** : `"saison": None` dans `CULTURES`. Limite connue : sur l'échantillon de Toulouse, les 20 jours de gel du maïs tombent entre décembre et mars, donc hors saison ; le GDD est surestimé. |
| **J4 (décidé)** | **Saison de la culture** : une seule période, du semis à la récolte, appliquée à tous les indicateurs de la culture (gel, GDD, stress thermique, bilan hydrique). |

**Mise en œuvre en J4 :**

- **Module (DATA) :** le paramètre `saison` de chaque culture dans `CULTURES` prend la valeur `(mois_debut, mois_fin)`, mois inclus. Le module gère déjà ce paramètre (test `test_saison_restreinte`).
- **Base (DATA) :** deux colonnes ajoutées à `Dim_Culture` : `mois_debut` et `mois_fin` (`TINYINT`, 1 à 12). Ajout par `ALTER TABLE` sur la base partagée, **jamais en relançant `creation_bdd.sql`** (il supprime toutes les tables). Le script `creation_bdd.sql` est mis à jour en parallèle.
- **Cohérence :** `test_coherence_dim_culture_sql` vérifie aussi que les mois de `Dim_Culture` sont identiques à ceux de `CULTURES`.
- **Application (DEV) :** le payload ne change pas, DEV envoie toujours les années complètes de l'horizon et le module ne garde que les mois de la saison. DEV ajoute `mois_debut` / `mois_fin` au modèle `DimCulture` et affiche la période sur la page de résultat (par exemple « calculé d'avril à octobre »).
- **Nom des colonnes :** la colonne `saison` de `Dim_Temps` (valeur `'annuel'`) désigne l'horizon, pas la saison de culture ; elle n'est pas utilisée pour ce calcul.

**Mois par culture (à sourcer par DATA) :**

| `id_culture` | Culture | `mois_debut` | `mois_fin` | Source |
|---|---|---|---|---|
| 1 | Maïs grain | à sourcer | à sourcer | à renseigner |
| 2 | Tournesol | à sourcer | à sourcer | à renseigner |
| 3 | Colza | à sourcer | à sourcer | à renseigner |
| 4 | Pomme de terre | à sourcer | à sourcer | à renseigner |

Chaque valeur pointe vers une source réelle (Arvalis, Terres Inovia, etc.), tracée dans `Source_Seuil` comme les autres seuils.

**Cultures d'hiver (colza) :** la saison passe le 31 décembre (par exemple de septembre à juillet), donc `mois_debut` > `mois_fin`. Le module accepte ce cas, mais il regroupe les jours par année civile : chaque année mélange la fin d'une campagne et le début de la suivante. Sur une moyenne de 11 ans, l'écart reste faible ; c'est une limite à connaître et à expliquer.

**Conséquence sur les valeurs de référence :** les résultats attendus des tests (gel 20, GDD 3136,9, stress 11 sur l'échantillon de Toulouse) changent pour le maïs. DATA les recalcule, ou garde ces tests en passant explicitement une saison vide au module.

---

## 5. Erreurs

Le module lève une `ValueError` avec un message explicite dans les cas suivants. DEV doit les attraper et afficher une erreur claire sans écrire en base : retour au formulaire avec un message dans l'interface, ou HTTP 400 pour une route d'API (voir 3.4).

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