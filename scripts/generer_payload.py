"""Génère un VRAI payload du contrat d'interface (DEV -> DATA) dans un fichier JSON.

À lancer depuis la racine du projet, venv activé, avec une connexion internet
(le script appelle réellement Open-Meteo) :

    python scripts/generer_payload.py
    python scripts/generer_payload.py --commune 13 --culture 1 --horizon 2 --sortie docs/extrait.json
    python scripts/generer_payload.py --jours 5 --sortie docs/extrait.json

Le fichier produit est à envoyer à DATA pour qu'ils vérifient que leur
fonction de calcul l'accepte (tâche 8).
"""
import argparse
import json
import sys
from pathlib import Path

# Permet de lancer le script depuis n'importe où : on ajoute la racine du
# projet au chemin de recherche des modules pour pouvoir faire `import app`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.payload import construire_payload

# Clés attendues par le contrat d'interface
CLES_CONTRAT = {
    "id_commune", "code_insee", "id_culture", "id_temps", "id_modele",
    "id_session", "id_utilisateur", "latitude", "series",
}
CLES_JOUR = {"date", "t_min", "t_max", "t_moy", "precip"}


def verifier_contrat(payload):
    """Renvoie la liste des écarts avec le contrat (liste vide = conforme)."""
    problemes = []
    if set(payload) != CLES_CONTRAT:
        problemes.append(f"clés différentes du contrat : {sorted(set(payload) ^ CLES_CONTRAT)}")
    if not payload.get("series"):
        problemes.append("series est vide")
    for jour in payload.get("series", []):
        if set(jour) != CLES_JOUR:
            problemes.append(f"jour mal formé : {jour}")
            break
    return problemes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Génère un payload du contrat d'interface.")
    parser.add_argument("--commune", type=int, default=13, help="id_commune (13 = Toulouse)")
    parser.add_argument("--culture", type=int, default=1, help="id_culture (1 = Maïs grain)")
    parser.add_argument("--horizon", type=int, default=2, help="id_temps (2 = horizon 2050)")
    parser.add_argument("--modele", type=int, default=1, help="id_modele (1 = MRI_AGCM3_2_S)")
    parser.add_argument("--sortie", default="payload_exemple.json", help="fichier JSON à écrire")
    parser.add_argument("--jours", type=int, default=None,
                        help="ne garder que les N premiers jours (extrait lisible) ; "
                             "par défaut toute la série")
    args = parser.parse_args(argv)

    # Construction du payload exactement comme le fait la page de résultat.
    try:
        payload = construire_payload(
            args.commune, args.culture, args.horizon, args.modele, "sess_demo"
        )
    except (ValueError, RuntimeError) as erreur:
        print(f"Échec : {erreur}")
        return 1

    # Contrôle de conformité AVANT troncature, sur la série complète.
    problemes = verifier_contrat(payload)
    series = payload["series"]
    manquantes = {
        champ: sum(1 for jour in series if jour[champ] is None)
        for champ in ("t_min", "t_max", "t_moy", "precip")
    }

    # Extrait éventuel (plus pratique à lire et à envoyer).
    if args.jours is not None:
        payload["series"] = series[: args.jours]

    with open(args.sortie, "w", encoding="utf-8") as fichier:
        json.dump(payload, fichier, ensure_ascii=False, indent=2)

    # Résumé dans le terminal.
    print(f"Fichier écrit : {args.sortie}")
    print(f"Commune {payload['id_commune']} (INSEE {payload['code_insee']}), "
          f"culture {payload['id_culture']}, horizon {payload['id_temps']}, "
          f"modèle {payload['id_modele']}")
    print(f"Série complète : {len(series)} jours, du {series[0]['date']} au {series[-1]['date']}")
    print(f"Jours écrits dans le fichier : {len(payload['series'])}")
    print(f"Valeurs manquantes (null) : {manquantes}")
    if problemes:
        print("ÉCARTS AVEC LE CONTRAT :")
        for probleme in problemes:
            print(f" - {probleme}")
        return 2
    print("Conforme au contrat (clés et champs de chaque jour).")
    return 0


if __name__ == "__main__":
    sys.exit(main())