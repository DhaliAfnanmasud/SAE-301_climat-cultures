# Contrat d'Interface DEV ⇄ DATA — SAÉ 3.01 (Climat & Cultures)

**Version :** 1.0
**Jalon :** Jalon 2 (Semaine 41)  
**Format retenu :** JSON ➔ JSON  
**Statut :** Validé (Conforme au schéma en étoile Datamart)

---

## 1. Objet du document

Ce contrat d'interface fixe le format standard des échanges de données structurées en **JSON** entre le pôle **DEV** (client API Open-Meteo & Back-End Flask) et le pôle **DATA** (module de calcul d'indicateurs & alimentation de la base de données).

---

## 2. Flux Entrant : Séries météo et paramètres (DEV ➔ DATA)

Le pôle DEV transmet au pôle DATA un objet JSON unique contenant le contexte d'analyse ainsi que la série météo journalière.

### 2.1 Spécification de la structure d'entrée

- **`id_commune`** (`int`) : Identifiant interne de la commune, clé étrangère vers `Dim_Commune`.
- **`code_insee`** (`string`, optionnel) : Code INSEE officiel de la commune.
- **`id_culture`** (`int`) : Identifiant de la culture, clé étrangère vers `Dim_Culture`.
- **`id_temps`** (`int`) : Identifiant de l'horizon temporel, clé étrangère vers `Dim_Temps`.
- **`id_modele`** (`int`) : Identifiant du modèle climatique, clé étrangère vers `Dim_Modele`.
- **`id_session`** (`string`, optionnel) : Identifiant de session utilisé pour rattacher les résultats à un visiteur anonyme.
- **`id_utilisateur`** (`int`, optionnel) : Identifiant du compte utilisateur connecté.
- **`series`** (`array`) : Liste d'objets représentant les mesures météo quotidiennes :
  - **`date`** (`string`) : Date au format `YYYY-MM-DD`.
  - **`t_min`** (`float` ou `null`) : Température minimale du jour en °C.
  - **`t_max`** (`float` ou `null`) : Température maximale du jour en °C.
  - **`t_moy`** (`float` ou `null`) : Température moyenne du jour en °C.
  - **`precip`** (`float` ou `null`) : Cumul quotidien des précipitations en mm.

### 2.2 Exemple de Payload JSON Entrant

```json
{
  "id_commune": 1,
  "code_insee": "75056",
  "id_culture": 1,
  "id_temps": 2,
  "id_modele": 1,
  "id_session": "sess_8f92a",
  "id_utilisateur": null,
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
