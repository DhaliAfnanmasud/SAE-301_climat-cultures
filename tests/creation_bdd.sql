-- ============================================================
-- SAE 3.01 - Climat & Cultures
-- Script de creation de la base de donnees (schema en etoile)
-- Pole DATA - S43
-- ============================================================
-- Ordre a respecter : 1) creation_bdd.sql   2) sources_seuils.sql
-- Attention : ce script supprime les tables au debut (DROP TABLE).
-- Il ne faut plus le relancer sur la base partagee quand Fact_Indicateur
-- contient des calculs, sinon on perd tout.
-- Pour modifier la base partagee : ALTER TABLE uniquement.

-- On supprime les anciennes tables pour pouvoir relancer le script.
-- On desactive les cles etrangeres le temps du DROP, sinon MySQL
-- refuse de supprimer une table qui est encore liee a une autre.
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Fact_Indicateur;
DROP TABLE IF EXISTS Utilisateur;
DROP TABLE IF EXISTS Source_Seuil;
DROP TABLE IF EXISTS Dim_Verdict;
DROP TABLE IF EXISTS Dim_Modele;
DROP TABLE IF EXISTS Dim_Temps;
DROP TABLE IF EXISTS Dim_Culture;
DROP TABLE IF EXISTS Dim_Commune;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================
-- LES DIMENSIONS
-- (les "axes" d'analyse autour de la table de faits)
-- ============================

-- Dim_Commune : les communes qu'on etudie.
-- Le code INSEE est unique pour chaque commune.
-- La latitude et la longitude servent a appeler l'API Open-Meteo.
CREATE TABLE Dim_Commune (
    id_commune        INT PRIMARY KEY AUTO_INCREMENT,
    code_insee        CHAR(5) NOT NULL UNIQUE,
    nom_commune       VARCHAR(100) NOT NULL,
    latitude          DECIMAL(8,5) NOT NULL,
    longitude         DECIMAL(8,5) NOT NULL,
    altitude_m        SMALLINT,
    zone_climatique   VARCHAR(50),
    remarque_agricole VARCHAR(150)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dim_Culture : les cultures et leurs seuils agronomiques.
-- Ces seuils sont croises avec les series climatiques pour calculer les indicateurs
-- (GDD, jours de gel, stress thermique...).
-- Les colonnes besoin_eau et temperature_optimale peuvent etre vides
-- (NULL) quand on n'a pas trouve de source fiable.
-- mois_debut / mois_fin : saison de la culture (semis -> recolte), mois inclus (1 a 12).
-- NULL = pas de saison, le calcul se fait sur l'annee entiere (saison_debut = 1, saison_fin = 12).
-- source_saison : d'ou viennent ces deux mois (tracabilite).
CREATE TABLE Dim_Culture (
    id_culture               INT PRIMARY KEY AUTO_INCREMENT,
    nom_culture              VARCHAR(50) NOT NULL,
    temperature_base         DECIMAL(4,1) NOT NULL,
    temperature_plafond      DECIMAL(4,1),                    -- plafond de t_max pour le GDD (NULL = pas de plafond)
    gdd_maturite             INT,
    seuil_gel                DECIMAL(4,1) NOT NULL,
    stade_gel_reference      VARCHAR(100),
    seuil_stress_thermique   DECIMAL(4,1),
    temperature_optimale_min DECIMAL(4,1),
    temperature_optimale_max DECIMAL(4,1),
    besoin_eau_min_mm        SMALLINT,
    besoin_eau_max_mm        SMALLINT,
    ordre_priorite_mvp       TINYINT,
    mois_debut               TINYINT,
    mois_fin                 TINYINT,
    source_saison            VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dim_Temps : les horizons de temps qu'on compare.
-- Un horizon = une periode d'environ 10 ans, bornes incluses (donc 11 annees civiles :
-- 2015-2025 pour la reference, 2040-2050 pour la projection).
CREATE TABLE Dim_Temps (
    id_temps     INT PRIMARY KEY AUTO_INCREMENT,
    horizon      VARCHAR(20) NOT NULL,
    annee_debut  SMALLINT NOT NULL,
    annee_fin    SMALLINT NOT NULL,
    saison       VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dim_Modele : les modeles climatiques utilises.
-- On en garde deux pour pouvoir comparer et voir l'incertitude.
-- code_api est le nom exact qu'on envoie a l'API.
CREATE TABLE Dim_Modele (
    id_modele    INT PRIMARY KEY AUTO_INCREMENT,
    code_api     VARCHAR(30) NOT NULL UNIQUE,
    nom_complet  VARCHAR(100),
    origine      VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dim_Verdict : les verdicts possibles pour une culture.
-- Comme il n'y a que 3 valeurs, j'ai fait une petite table
-- plutot que d'ecrire du texte libre dans la table de faits.
CREATE TABLE Dim_Verdict (
    id_verdict   INT PRIMARY KEY AUTO_INCREMENT,
    libelle      VARCHAR(30) NOT NULL UNIQUE,
    description  VARCHAR(150)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Source_Seuil : d'ou vient chaque seuil (tracabilite).
-- Une ligne = un seuil d'une culture avec sa source, son niveau de confiance,
-- le lien et la date a laquelle on a consulte la source.
-- Elle est remplie par le fichier sources_seuils.sql.
CREATE TABLE Source_Seuil (
    id_source_seuil  INT PRIMARY KEY AUTO_INCREMENT,
    id_culture       INT NOT NULL,
    nom_seuil        VARCHAR(50) NOT NULL,
    valeur           VARCHAR(50) NOT NULL,   -- en texte car parfois c'est une fourchette (ex : -7 a -2)
    unite            VARCHAR(20),
    stade_fenetre    VARCHAR(100),
    source           VARCHAR(150) NOT NULL,
    niveau_confiance VARCHAR(30) NOT NULL,
    remarque         TEXT,
    source_url       VARCHAR(255),
    date_consultee   DATE,
    FOREIGN KEY (id_culture) REFERENCES Dim_Culture(id_culture)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================
-- COMPTES UTILISATEURS (RGPD)
-- C'est la seule table avec des donnees personnelles (l'email).
-- Le reste de la base n'en contient pas.
-- ============================

CREATE TABLE Utilisateur (
    id_utilisateur      INT PRIMARY KEY AUTO_INCREMENT,
    email               VARCHAR(150) NOT NULL UNIQUE,
    mot_de_passe_hash   VARCHAR(255) NOT NULL,        -- on ne stocke jamais le mot de passe en clair, DEV le hache avant
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consentement_rgpd   BOOLEAN NOT NULL DEFAULT FALSE,
    date_consentement   DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================
-- LA TABLE DE FAITS (le centre de l'etoile)
-- Une ligne = les indicateurs d'une commune pour une culture,
-- sur un horizon, avec un modele, sur une saison (et pour une session ou un utilisateur).
-- ============================

CREATE TABLE Fact_Indicateur (
    id_fait                 INT PRIMARY KEY AUTO_INCREMENT,
    id_commune              INT NOT NULL,
    id_culture              INT NOT NULL,
    id_temps                INT NOT NULL,
    id_modele               INT NOT NULL,
    id_verdict              INT,
    id_session              VARCHAR(64) NOT NULL DEFAULT '',  -- NOT NULL, sinon la contrainte UNIQUE ne bloque pas les doublons
    id_utilisateur          INT,                              -- entier, FK vers Utilisateur (voir CONTRAT_INTERFACE.md)
    jours_gel               DECIMAL(5,1),                     -- c'est une moyenne sur 10 ans, donc il faut des decimales
    gdd                     DECIMAL(6,1),
    jours_stress_thermique  DECIMAL(5,1),                     -- pareil, moyenne sur l'horizon
    bilan_hydrique_mm       DECIMAL(6,1),
    date_calcul             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- saison utilisee pour le calcul (mois inclus). 1 et 12 = annee entiere.
    -- NOT NULL : sinon la contrainte UNIQUE ne bloque pas les doublons.
    saison_debut            TINYINT NOT NULL DEFAULT 1,
    saison_fin              TINYINT NOT NULL DEFAULT 12,

    -- liens vers les 5 dimensions
    FOREIGN KEY (id_commune) REFERENCES Dim_Commune(id_commune),
    FOREIGN KEY (id_culture) REFERENCES Dim_Culture(id_culture),
    FOREIGN KEY (id_temps)   REFERENCES Dim_Temps(id_temps),
    FOREIGN KEY (id_modele)  REFERENCES Dim_Modele(id_modele),
    FOREIGN KEY (id_verdict) REFERENCES Dim_Verdict(id_verdict),
    -- ON DELETE CASCADE : si on supprime un compte, ses calculs sont supprimes aussi
    -- (c'est le droit a l'effacement du RGPD)
    FOREIGN KEY (id_utilisateur) REFERENCES Utilisateur(id_utilisateur) ON DELETE CASCADE,

    -- on ne veut pas deux fois le meme calcul pour la meme combinaison (saison comprise)
    UNIQUE KEY uq_fait (id_commune, id_culture, id_temps, id_modele, id_session, saison_debut, saison_fin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- REMPLISSAGE DES DIMENSIONS
-- ============================================================

-- 16 communes avec des climats differents (source : communes-reference.csv)
INSERT INTO Dim_Commune (code_insee, nom_commune, latitude, longitude, altitude_m, zone_climatique, remarque_agricole) VALUES
('59350', 'Lille',            50.63,  3.06,   25, 'océanique dégradé',  'Flandre - betterave et blé'),
('29019', 'Brest',            48.39, -4.49,   50, 'océanique',          'Littoral ouest - polyculture élevage'),
('35238', 'Rennes',           48.11, -1.68,   30, 'océanique',          'Bretagne - polyculture élevage'),
('51454', 'Reims',            49.26,  4.03,   85, 'océanique dégradé',  'Champagne - vigne'),
('75056', 'Paris',            48.85,  2.35,   35, 'océanique dégradé',  'Bassin parisien - îlot de chaleur urbain'),
('45234', 'Orléans',          47.90,  1.90,  100, 'océanique dégradé',  'Beauce - grandes cultures céréalières'),
('67482', 'Strasbourg',       48.58,  7.75,  140, 'semi-continental',   "Plaine d'Alsace - maïs"),
('54395', 'Nancy',            48.69,  6.18,  210, 'semi-continental',   'Lorraine - polyculture'),
('21231', 'Dijon',            47.32,  5.04,  245, 'semi-continental',   'Bourgogne - vigne'),
('63113', 'Clermont-Ferrand', 45.78,  3.08,  330, 'semi-continental',   'Limagne - céréales'),
('69123', 'Lyon',             45.76,  4.84,  170, 'semi-continental',   'Vallée du Rhône'),
('33063', 'Bordeaux',         44.84, -0.58,   10, 'océanique aquitain', 'Sud-Ouest - vigne et maïs'),
('31555', 'Toulouse',         43.60,  1.44,  150, 'océanique aquitain', 'Sud-Ouest - céréales tournesol maïs'),
('84007', 'Avignon',          43.95,  4.81,   25, 'méditerranéen',      'Vallée du Rhône - vergers vigne maraîchage'),
('34172', 'Montpellier',      43.61,  3.88,   30, 'méditerranéen',      'Languedoc - vigne'),
('05023', 'Briançon',         44.90,  6.64, 1326, 'montagnard',         'Alpes - alpages - ville la plus haute de France');

-- 4 cultures, dans l'ordre de priorite pour le MVP (source : la fiche de seuils de l'equipe).
-- Choix que j'ai faits :
--  - pomme de terre : base 5 et pas 6, parce que le GDD de 1050 de la fiche est calcule en base 5
--  - colza : stress thermique a 29, c'est le seuil critique de la fiche (25 = seulement une alerte)
--  - tournesol : gel a -4, valeur intermediaire de la fourchette -7 a -2 (les sources ne sont pas d'accord ;
--    ce n'est PAS la valeur la plus prudente, qui serait -2) -> point a arbitrer, voir fiche de seuils 8.1
--  - temperature_plafond : 30 pour le mais (cumul plafonne a 30 C), NULL pour les autres cultures
--  Ces valeurs doivent rester identiques a CULTURES dans calcul_indicateurs.py (test_coherence_dim_culture_sql).
--  - mois_debut / mois_fin : saison de la culture (semis -> recolte), NULL = annee entiere (colza : recolte non sourcee)
INSERT INTO Dim_Culture
(nom_culture, temperature_base, temperature_plafond, gdd_maturite, seuil_gel, stade_gel_reference, seuil_stress_thermique, temperature_optimale_min, temperature_optimale_max, besoin_eau_min_mm, besoin_eau_max_mm, ordre_priorite_mvp, mois_debut, mois_fin, source_saison) VALUES
('Maïs grain',      6.0, 30.0, 1600,   0.0, 'avant 5-6 feuilles',            35.0, 25.0, 30.0, NULL, NULL, 1, 4, 10, 'Terre-net : semis mi-avril à mi-mai, récolte fin septembre (semis précoces), mois_fin = 10 non sourcé précisément'),
('Tournesol',       6.0, NULL, 1500,  -4.0, 'stade cotylédons (-7 à -2°C)',  34.0, 20.0, 27.0,  230,  230, 2, 3, 10, 'Terres Inovia guide tournesol 2026 (semis dès fin mars), Réussir (récolte fin août à mi-octobre)'),
('Colza',           0.0, NULL, 2330, -15.0, 'bien implanté (létal : -18°C)', 29.0, 10.0, 30.0,  600,  650, 3, NULL, NULL, 'Semis en août (Terres Inovia 2025), récolte non sourcée : année entière'),
('Pomme de terre',  5.0, NULL, 1050,  -2.0, 'stade feuillage',               28.0, NULL, 18.0,  350,  450, 4, 3, 9, 'La CAB, fiche technique pomme de terre : plantation mi-mars, récolte mi-juillet à fin septembre');

-- 2 modeles climatiques : un de reference et un pour comparer
INSERT INTO Dim_Modele (code_api, nom_complet, origine) VALUES
('MRI_AGCM3_2_S', 'MRI-AGCM3.2S',  'MRI, Japon - modèle de référence, le plus complet'),
('CMCC_CM2_VHR4', 'CMCC-CM2-VHR4', 'CMCC, Italie - modèle de comparaison');

-- 2 horizons : la periode de reference et la projection 2050
-- (la colonne saison de Dim_Temps = 'annuel' designe l'horizon, pas la saison de culture)
INSERT INTO Dim_Temps (horizon, annee_debut, annee_fin, saison) VALUES
('reference', 2015, 2025, 'annuel'),
('2050',      2040, 2050, 'annuel');

-- les 3 verdicts, il faut les mettre avant de faire des calculs
INSERT INTO Dim_Verdict (libelle, description) VALUES
('viable',     'La culture reste viable sur cet horizon, selon les seuils retenus'),
('menacee',    'Viabilité incertaine : au moins un indicateur approche un seuil critique'),
('non_viable', 'Au moins un seuil critique est dépassé de façon récurrente sur cet horizon');

-- Source_Seuil est remplie ensuite par le fichier sources_seuils.sql (31 seuils sources)