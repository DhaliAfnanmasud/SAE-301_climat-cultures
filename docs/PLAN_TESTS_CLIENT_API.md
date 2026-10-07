# Plan de tests — Client API Open-Meteo

## SAÉ 3.01 — Climat & Cultures

**Jalon :** J2.2  
**Pôle :** DEV  
**Outil prévu :** pytest

---

## 1. Objectif

Ce plan de tests a pour but de vérifier que notre client Open-Meteo fonctionne correctement avant son intégration complète dans l'application.

On veut principalement vérifier que les données climatiques sont bien récupérées, que les erreurs sont correctement gérées, que le cache évite les appels inutiles et que les données envoyées au pôle DATA respectent bien notre contrat d'interface.

Les calculs des indicateurs ne sont pas testés ici car ils sont réalisés par le pôle DATA.

---

## 2. Cas de tests prévus

| ID  | Cas testé                     | Situation                                        | Résultat attendu                                                                  |
| --- | ----------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------- |
| T01 | Requête valide                | Commune, dates et modèle valides                 | Les données climatiques sont récupérées correctement                              |
| T02 | Commune inconnue              | La commune n'existe pas                          | La demande est refusée avant l'appel à Open-Meteo                                 |
| T03 | Modèle inconnu                | Le modèle n'existe pas                           | La demande est refusée avant l'appel à Open-Meteo                                 |
| T04 | Dates incohérentes            | La date de début est après la date de fin        | La demande est refusée avec une erreur claire                                     |
| T05 | Format des séries             | Open-Meteo retourne une réponse valide           | Chaque journée contient `date`, `t_min`, `t_max`, `t_moy` et `precip`             |
| T06 | Respect du contrat DEV ⇄ DATA | Les séries sont prêtes à être envoyées à DATA    | Le JSON contient les identifiants obligatoires et la liste `series` au bon format |
| T07 | Valeur manquante              | Une température ou une précipitation vaut `null` | La valeur reste `null` et n'est pas remplacée par une valeur inventée             |
| T08 | Problème réseau / timeout     | Open-Meteo ne répond pas                         | Le client réessaie 2 fois puis retourne un message d'indisponibilité              |
| T09 | Erreur serveur 500            | Open-Meteo retourne une erreur 500               | Le client réessaie 2 fois puis retourne un message d'indisponibilité              |
| T10 | Erreur 429                    | Trop de requêtes sont envoyées                   | Le client ne réessaie pas et indique que le service est saturé                    |
| T11 | Réponse vide ou incomplète    | Les données attendues sont absentes              | Le client indique que les données sont indisponibles                              |
| T12 | Cache existant                | La même requête a déjà été effectuée             | La réponse est récupérée dans le cache sans rappeler Open-Meteo                   |
| T13 | Nouvelle requête              | Un paramètre change                              | Le cache précédent n'est pas utilisé et Open-Meteo est appelé                     |
| T14 | Erreur et cache               | L'appel à Open-Meteo échoue                      | La réponse en erreur n'est pas enregistrée dans le cache                          |

---

## 3. Vérification du contrat DEV ⇄ DATA

Le format envoyé au pôle DATA doit respecter le contrat d'interface version 1.0.

Exemple simplifié :

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

Nous vérifierons notamment que :

- `id_commune`, `id_culture`, `id_temps` et `id_modele` sont présents ;
- `code_insee`, `id_session` et `id_utilisateur` peuvent être optionnels ;
- les dates respectent le format `YYYY-MM-DD` ;
- les températures sont exprimées en °C ;
- les précipitations sont exprimées en mm ;
- une donnée météo absente reste à `null`.

---

## 4. Tests du cache

Le cache doit éviter de refaire plusieurs fois exactement la même requête.

Nous vérifierons qu'une première requête appelle Open-Meteo et enregistre une réponse valide dans le cache. Une deuxième requête avec les mêmes paramètres doit utiliser cette réponse sans rappeler l'API.

Si la commune, les dates, le modèle ou les variables changent, une nouvelle requête doit être effectuée.

Les réponses en erreur ne doivent jamais être enregistrées dans le cache.

---

## 5. Méthode de test

Les tests seront réalisés avec `pytest`.

Pour la majorité des cas, nous utiliserons des réponses Open-Meteo simulées. Cela nous permettra de tester facilement un timeout, une erreur 500, une erreur 429 ou une réponse vide sans provoquer volontairement ces erreurs sur l'API réelle. Cela nous permettera également de ne pas épuiser le quota d'appels API journalier qui est de 10000.

Nous garderons aussi un test utilisant réellement Open-Meteo afin de vérifier que notre client arrive bien à récupérer des données climatiques.

Les tests seront regroupés dans :

```text
tests/test_openmeteo_client.py
```

Ils pourront être lancés avec :

```bash
pytest tests/test_openmeteo_client.py
```

---

## 6. Critères de réussite

Le client sera considéré comme fonctionnel si une requête correcte renvoie les séries attendues, si les mauvaises entrées sont refusées, si les erreurs sont gérées sans faire planter l'application et si le cache fonctionne correctement.

Les données produites doivent également respecter le contrat DEV ⇄ DATA afin que le pôle DATA puisse les utiliser directement pour ses calculs.

Ce plan pourra être complété pendant le développement si nous rencontrons de nouveaux cas particuliers.
