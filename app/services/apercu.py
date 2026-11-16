def _moyenne(valeurs):
    """Moyenne arrondie à 0,1 ; None s'il n'y a aucune valeur."""
    return round(sum(valeurs) / len(valeurs), 1) if valeurs else None


def agreger_par_mois(series):
    """Résume les séries journalières du payload en valeurs mensuelles.

    Sur 11 ans, un graphique journalier ferait envrion 4000 points illisibles.
    On affiche donc par mois : la moyenne de t_min / t_max / t_moy et le
    cumul de précipitations. Les jours sans valeur (None) sont ignorés ;
    un mois sans aucune valeur reste à None (jamais 0).

    Renvoie {"labels": ["2040-01", ...], "t_min": [...], "t_max": [...],
             "t_moy": [...], "precip": [...]} prêt pour Chart.js.
    """
    
    # On regroupe les valeurs de chaque jour sous la clé "AAAA-MM".
    par_mois = {}
    for jour in series:
        mois = par_mois.setdefault(
            jour["date"][:7],
            {"t_min": [], "t_max": [], "t_moy": [], "precip": []},
        )
        for champ, valeurs in mois.items():
            if jour[champ] is not None:
                valeurs.append(jour[champ])

    resultat = {"labels": [], "t_min": [], "t_max": [], "t_moy": [], "precip": []}
    for cle in sorted(par_mois):  # les clés ISO se trient dans l'ordre du temps
        mois = par_mois[cle]
        resultat["labels"].append(cle)
        resultat["t_min"].append(_moyenne(mois["t_min"]))
        resultat["t_max"].append(_moyenne(mois["t_max"]))
        resultat["t_moy"].append(_moyenne(mois["t_moy"]))
        # Précipitations : on additionne (cumul mensuel), on ne fait pas la moyenne.
        resultat["precip"].append(
            round(sum(mois["precip"]), 1) if mois["precip"] else None
        )
    return resultat