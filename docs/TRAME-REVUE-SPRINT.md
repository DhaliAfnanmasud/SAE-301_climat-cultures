# 🔁 Revue de sprint — Équipe 1 — Sprint n° 1

- **Période :** du 09/11/2026 au 29/11/2026
- **Présents :** BOUSSAIDI Malik, DHALI Afnanmasud, EL AIDOUS Amine, ELGHOMARI--JABEUR Alaeddine, LIN Romaric

## 1. Objectifs prévus pour ce sprint
- Mettre en place la conformité RGPD de la base (jalon 3.1)
- Calculer un premier indicateur et l'écrire dans la base (jalon 3.2)
- Intégrer le module de calcul de DATA dans l'appli et la déployer sur AlwaysData (jalon 3.3)

## 2. Réalisé

**💻 Pôle DEV**
- Fait : `[à compléter avec le DEV : appli Flask, appel du module, etc.]`
- En cours / non fait : `[déploiement sur AlwaysData si pas encore en ligne]`

**📊 Pôle DATA**
- Fait :
  - Requêtes RGPD corrigées et testées sur la base.
  - Jalon 3.2 : calcul des jours de gel (Toulouse, maïs, 2010 : 20 jours), écrits dans `Fact_Indicateur` (session `S47_gel`).
  - Module `calcul_indicateurs.py` : jours de gel, GDD, jours de stress thermique, bilan hydrique et verdict.
  - Test du module sur le `payload.json` du DEV (Toulouse, maïs, 2050, MRI) : gel 6.7, GDD 3514.6, stress 14.7, bilan −241.4 mm, verdict viable.
  - Écriture en base testée avec `ecrire_fact` sur la vraie base.
  - Réponses aux 5 questions du DEV et relecture du contrat d'interface v1.3.
- En cours / non fait :
  - Date et validation à ajouter dans le contrat d'interface.
  - Test en ligne avec le DEV une fois l'appli déployée.
  - Changement du mot de passe de la base (à faire avec l'équipe).

**👥 Intégration commune**
- `[À remplir après le test en ligne : ce qui s'affiche sur le site pour Toulouse / maïs / 2050 / MRI. Si ce n'est pas encore en ligne, écrire "en cours".]`

## 3. Démonstration
- Ce qui a été montré : `[choix d'une commune sur le site en ligne et affichage d'un indicateur réel — seulement si le test a été fait]`
- Retour / remarques : `[…]`

## 4. Obstacles & décisions
- Obstacles rencontrés : le DEV annonçait des valeurs nulles dans le payload alors qu'il n'y en avait pas ; erreur de connexion à la base (mot de passe mal saisi), corrigée ; `[déploiement AlwaysData]`
- Décisions prises : calcul sur l'année entière pour J3 (saison de culture prévue en J4) ; jour de gel = température min strictement sous le seuil ; une année est complète à partir de 90 % de jours ; bilan hydrique calculé seulement si la latitude est donnée.

## 5. Indicateurs
- Avancement vs prévu : `[ex. 80 %]`
- 🌱 Usage IA sur le sprint : `[tokens consommés / budget restant — à regarder dans le journal IA]`

## 6. Plan du prochain sprint
- Priorités : calcul sur la saison de culture (`mois_debut` / `mois_fin` par culture), sourcer les seuils manquants, finir l'intégration.
- Répartition DEV / DATA : `[…]`

## 7. Point d'équipe
- Ce qui a bien marché : contrat d'interface commun, module testé sur un vrai payload.
- À améliorer (collaboration, méthode) : `[ex. prévenir plus tôt quand une tâche bloque l'autre]`