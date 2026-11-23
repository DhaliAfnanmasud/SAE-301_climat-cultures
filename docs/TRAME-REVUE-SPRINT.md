# Revue de sprint — Équipe 1 — Sprint n° 1

- **Période :** du 09/11/2026 au 29/11/2026
- **Présents :** BOUSSAIDI Malik, DHALI Afnanmasud, EL AIDOUS Amine, ELGHOMARI--JABEUR Alaeddine, LIN Romaric
- **Version déployée :** https://sae301climat.alwaysdata.net/
- **Contrat d'interface DEV ↔ DATA :** v1.3, daté du 23/11/2026

## 1. Objectifs prévus pour ce sprint

- Mettre en place la conformité RGPD de la base (jalon 3.1).
- Calculer un premier indicateur et l'écrire dans la base (jalon 3.2).
- Intégrer le module de calcul de DATA dans l'application et déployer le MVP sur AlwaysData (jalon 3.3).

## 2. Réalisé

### Pôle DEV

- Mise en place et amélioration de l'application Flask avec les différentes pages et la navigation.
- Création du tableau de bord permettant de choisir une commune, une culture et un horizon temporel.
- Les communes, cultures, horizons et modèles sont récupérés directement depuis les tables de dimensions de la base de données.
- Validation côté serveur des données envoyées par le formulaire afin de refuser les identifiants inexistants ou modifiés manuellement.
- Mise en place du client Open-Meteo côté back-end.
- Ajout d'un système de cache afin d'éviter de refaire inutilement les mêmes appels à Open-Meteo.
- Gestion des erreurs liées à Open-Meteo, à la base de données et aux données saisies afin d'éviter l'affichage d'une erreur 500 à l'utilisateur.
- Transformation des données récupérées depuis Open-Meteo dans le format défini par le contrat d'interface DEV ↔ DATA.
- Intégration du module `calcul_indicateurs.py` fourni par le pôle DATA et appel de `calculer_indicateurs(payload)` depuis la route de résultat.
- Intégration de l'écriture des résultats dans `Fact_Indicateur`.
- Affichage sur la page résultat des indicateurs calculés :
  - jours de gel ;
  - degrés-jours de croissance (GDD) ;
  - jours de stress thermique ;
  - bilan hydrique.
- Affichage du verdict de viabilité de la culture.
- Affichage d'un graphique climatique avec Chart.js.
- Ajout d'un avertissement précisant qu'il s'agit d'une projection provenant d'un modèle climatique, issue d'un seul scénario d'émissions proche du plus pessimiste, et qu'elle doit être interprétée comme une tendance.
- Ajout de la source Open-Meteo et de la licence CC BY 4.0.
- Ajout de tests `pytest` pour le formulaire, les routes, le client API, le cache, les calculs et l'intégration générale.
- Préparation de la configuration de production avec `ProdConfig`, `FLASK_ENV`, `SECRET_KEY` et `DATABASE_URL`.
- Déploiement de l'application sur AlwaysData en Python WSGI.
- Configuration des variables d'environnement nécessaires sur le serveur.
- Validation du parcours complet sur la version en ligne (https://sae301climat.alwaysdata.net/).

### Pôle DATA

- Requêtes RGPD corrigées et testées sur la base.
- Jalon 3.2 : calcul des jours de gel pour Toulouse, maïs, 2010 : **20 jours**, écrits dans `Fact_Indicateur` avec la session `S47_gel`.
- Création du module `calcul_indicateurs.py` permettant de calculer :
  - les jours de gel ;
  - les GDD ;
  - les jours de stress thermique ;
  - le bilan hydrique ;
  - le verdict.
- Test du module sur le `payload.json` fourni par le DEV pour Toulouse, maïs, 2050 et le modèle MRI (valeurs moyennes annuelles sur les années complètes de la série ; une année à moins de 90 % des jours est exclue) :
  - gel : **6,7** ;
  - GDD : **3514,6** ;
  - stress thermique : **14,7** ;
  - bilan hydrique : **−241,4 mm** ;
  - verdict : **viable**.
- Écriture en base testée avec `ecrire_fact` sur la base réelle.
- Réponses aux questions du pôle DEV concernant l'intégration.
- Relecture et validation du contrat d'interface DEV ↔ DATA v1.3.

### Intégration commune

L'intégration de bout en bout est fonctionnelle.

Le parcours réalisé est le suivant :

1. L'utilisateur accède au tableau de bord.
2. Il choisit une commune, une culture et un horizon.
3. L'application récupère les informations correspondantes dans la base de données.
4. Le client back-end interroge Open-Meteo avec les coordonnées de la commune.
5. Les données climatiques sont transformées dans le format défini par le contrat d'interface.
6. Le payload est envoyé au module de calcul du pôle DATA.
7. Les indicateurs sont calculés à partir des séries climatiques et des seuils de la culture.
8. Les résultats sont enregistrés dans `Fact_Indicateur` par « upsert » lorsque la variable d'environnement `ENREGISTRER_FACT=1` est définie (désactivé par défaut ; un échec d'écriture est journalisé et n'empêche pas l'affichage).
9. L'utilisateur voit les indicateurs, le verdict et le graphique sur la page résultat.

Le site est maintenant déployé sur AlwaysData et ce parcours est disponible sur la version en ligne.

## 3. Démonstration

### Ce qui a été montré

- Accès au site déployé sur AlwaysData.
- Accès au tableau de bord.
- Sélection d'une commune, d'une culture et d'un horizon.
- Récupération des vraies données climatiques depuis Open-Meteo.
- Calcul des indicateurs avec le module DATA.
- Affichage des jours de gel, des GDD, des jours de stress thermique et du bilan hydrique.
- Affichage du verdict de viabilité.
- Affichage du graphique climatique.
- Gestion propre des erreurs lorsqu'un service ou une donnée pose problème.

### Retour / remarques

Le MVP demandé pour le J3 fonctionne de bout en bout. Nous avons privilégié le fonctionnement complet de la chaîne avant d'ajouter davantage de fonctionnalités.

Le résultat reste une projection climatique et non une prévision exacte. Les indicateurs du J3 sont également calculés sur l'année entière. La prise en compte plus précise de la saison propre à chaque culture est prévue pour la suite du projet. La règle du verdict est provisoire (jours de stress thermique et GDD de maturité) et sera remplacée par la règle validée par l'équipe.

## 4. Obstacles & décisions

### Obstacles rencontrés

- Au début de l'intégration, le pôle DEV pensait que certaines valeurs du payload étaient `null`, alors que le problème venait d'une inadéquation de format : l'API Open-Meteo renvoie des tableaux parallèles (`time`, `temperature_2m_min`, etc.). Ces tableaux ont été transformés en une liste de jours (`date`, `t_min`, `t_max`, `t_moy`, `precip`) conforme au contrat d'interface, directement exploitable par le pôle DATA, sans altération ni valeur inventée (une valeur absente reste `null`).
- Une erreur de connexion à la base a été rencontrée à cause d'un mot de passe mal saisi, puis corrigée.
- Plusieurs membres du pôle DEV travaillaient parfois sur les mêmes fichiers, notamment `app/blueprints/analyse/routes.py`, ce qui demandait de faire attention aux conflits Git pendant les merges.
- Il a fallu adapter la configuration entre le développement local et le déploiement sur AlwaysData.
- Les variables d'environnement de production ont dû être séparées du code afin de ne pas stocker de secrets dans Git.
- L'intégration entre le client Open-Meteo, le format du payload, le module DATA et la base a demandé plusieurs tests afin de vérifier que chaque partie communiquait correctement avec la suivante.

### Décisions prises

- Pour le J3, les indicateurs sont calculés sur l'année entière. La saison propre à chaque culture sera prise en compte lors du J4.
- Un jour de gel correspond à une température minimale strictement inférieure au seuil de gel de la culture.
- Une année est considérée comme suffisamment complète lorsque au moins 90 % des jours nécessaires sont disponibles.
- Le bilan hydrique est égal aux précipitations moins l'évapotranspiration estimée par la formule de Hargreaves-Samani (à partir des températures et de la latitude ; le champ ET0 d'Open-Meteo n'est pas utilisé). Il n'est calculé que si la latitude est disponible.
- Cas limites gérés par le module : valeur manquante ou incohérente (t_min > t_max) → jour ignoré et compté dans `nb_jours_ignores` ; année sans gel → 0 jour ; journée exactement au seuil → non comptée comme gel (comparaison stricte), mais comptée comme stress thermique (comparaison ≥) ; année incomplète (< 90 %) → exclue de la moyenne.
- Le scénario d'émissions est unique (Open-Meteo n'en propose qu'un, proche du plus pessimiste) : il est affiché comme tel et jamais comme « médian ».
- Les identifiants provenant du formulaire sont vérifiés côté serveur avant le lancement du calcul.
- Les erreurs provenant de l'API ou de la base doivent être affichées proprement à l'utilisateur et ne doivent pas provoquer une page 500.
- Les secrets et informations de connexion sont stockés dans les variables d'environnement et non dans le dépôt Git.
- Le contrat d'interface DEV ↔ DATA sert de référence commune afin d'éviter les différences de noms de champs ou de format entre les deux pôles.

## 5. Indicateurs

- **Avancement par rapport aux objectifs du sprint :** 3 jalons sur 3 réalisés (3.1 requêtes RGPD corrigées et testées sur la base ; 3.2 ; 3.3).
- **Tests :** suite `pytest` dans `tests/` (analyse, calcul des indicateurs, client Open-Meteo, payload, références, tableau de bord) : 101 tests, tous passent (exécution du 23/11/2026).
- **Usage IA sur le sprint :** voir les journaux IA individuels des membres de l'équipe. Le nombre exact de tokens n'étant pas directement mesurable dans notre utilisation de nos IA, il est indiqué comme `non mesurable` lorsque nécessaire.

## 6. Plan du prochain sprint

### Priorités

- Prendre en compte la vraie saison de culture grâce aux informations `mois_debut` et `mois_fin`.
- Compléter et mieux sourcer les seuils agricoles manquants : en cas d'écart faible entre sources, retenir la valeur la plus prudente et noter la fourchette ; sans source, conserver la valeur et écrire « non sourcé ».
- Comparer l'ET0 Hargreaves à une valeur de référence.
- Valider la règle de verdict (actuellement provisoire).
- Activer et vérifier l'écriture dans `Fact_Indicateur` sur la version en ligne.
- Ajouter ou améliorer les indicateurs.
- Comparer différents modèles ou horizons climatiques.
- Améliorer progressivement l'interface et la restitution des résultats.
- Continuer à renforcer les tests automatisés.

### Répartition DEV / DATA

**DEV :**

- adapter l'application aux nouveaux calculs du J4 ;
- faire évoluer les formulaires et les pages de résultat si nécessaire ;
- maintenir le déploiement AlwaysData ;
- renforcer la gestion des erreurs ;
- améliorer la restitution et la comparaison des résultats ;
- maintenir et compléter les tests.

**DATA :**

- ajouter la gestion de la saison propre à chaque culture ;
- compléter et sourcer les seuils nécessaires ;
- faire évoluer les calculs et les indicateurs ;
- fournir des jeux d'essais permettant de vérifier les nouveaux résultats.

## 7. Point d'équipe

### Ce qui a bien marché

- Mise en place d'un contrat d'interface commun entre DEV et DATA.
- Utilisation d'un vrai payload DEV pour tester le module DATA.
- Communication régulière entre les deux pôles pendant l'intégration.
- Découpage du développement en plusieurs parties : formulaire, API, calcul, base et affichage.
- Utilisation de branches Git permettant de travailler en parallèle.
- Mise en place de nombreux tests avant le déploiement.
- Le MVP final fonctionne réellement de bout en bout.

### À améliorer

- Éviter autant que possible que plusieurs personnes modifient simultanément les mêmes fichiers.
- Faire les merges plus régulièrement afin d'éviter des différences trop importantes entre les branches.
- Valider les contrats et formats d'échange encore plus tôt avant de commencer l'intégration.
- Continuer à documenter clairement les décisions communes entre DEV et DATA.
- Versionner et dater chaque évolution du contrat d'interface, et poser un tag Git à chaque jalon.
