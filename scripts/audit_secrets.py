"""Audit des secrets : y a-t-il un mot de passe ou une clé dans le dépôt Git ?

À lancer depuis la racine du projet :

    python scripts/audit_secrets.py

Il vérifie, sur TOUT l'historique (toutes les branches) :
  1. qu'aucun fichier .env n'est suivi par Git ;
  2. qu'aucune valeur sensible du .env (mot de passe, clé, jeton) n'est
     apparue dans un commit, ni dans .env.example ;
  3. qu'aucune ligne du genre  mot_de_passe = "..."  ou  mysql://user:mdp@hote
     n'a été ajoutée (hors tests/ et valeurs d'exemple).

Il n'affiche JAMAIS une valeur secrète : seulement le nom de la variable, le commit et le fichier. 
Code retour : 0 = rien trouvé, 1 = problème.

Si un secret est trouvé : le supprimer du dépôt NE SUFFIT PAS (il reste dans
l'historique). Il faut CHANGER ce mot de passe ou cette clé.
"""
import re
import subprocess
import sys
from pathlib import Path

# Variables du .env dont la valeur est secrète (le nom contient l'un de ces mots).
MOTS_SENSIBLES = ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "PASSWD")
LONGUEUR_MIN_VALEUR = 6  # en dessous, trop de faux positifs (« dev », « 1 »...)

# Valeurs d'exemple, volontairement présentes dans le code ou la doc.
VALEURS_D_EXEMPLE = {
    "cle-secrete-dev", "mot-de-passe-factice", "hash_factice", "change-moi",
    "une-chaine-quelconque-pour-le-developpement", "UTILISATEUR", "MOTDEPASSE",
}

# Marqueurs de remplacement du genre MOT_DE_PASSE, UTILISATEUR, <votre-mot-de-passe>.
MOTIF_MARQUEUR = re.compile(r"[A-Z_\-]+|<.*>|\$\{.*\}")


def _est_un_exemple(valeur):
    return valeur in VALEURS_D_EXEMPLE or bool(MOTIF_MARQUEUR.fullmatch(valeur))


MOTIF_AFFECTATION = re.compile(
    r"""(password|passwd|mot_de_passe|secret_key|api[_-]?key|token)\s*[=:]\s*["']([^"']{4,})["']""",
    re.IGNORECASE,
)
MOTIF_URL_AVEC_MOT_DE_PASSE = re.compile(r"(mysql|postgres|mariadb)[a-z+]*://[^\s:/@]+:([^\s@]+)@", re.IGNORECASE)


def _git(racine, *arguments):
    resultat = subprocess.run(
        ["git", *arguments], cwd=racine, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return resultat.stdout


def _valeurs_sensibles_du_env(racine):
    """{nom_de_variable: valeur} pour les variables secrètes du .env local."""
    fichier = Path(racine) / ".env"
    valeurs = {}
    if not fichier.exists():
        return valeurs
    for ligne in fichier.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in ligne or ligne.lstrip().startswith("#"):
            continue
        nom, valeur = ligne.split("=", 1)
        nom, valeur = nom.strip(), valeur.strip().strip('"').strip("'")
        if len(valeur) >= LONGUEUR_MIN_VALEUR and any(mot in nom.upper() for mot in MOTS_SENSIBLES):
            valeurs[nom] = valeur
    return valeurs


def auditer(racine):
    """Renvoie la liste des problèmes trouvés (liste vide = rien à signaler)."""
    problemes = []

    # 1. Un .env suivi par Git, à n'importe quel endroit du dépôt
    for chemin in _git(racine, "ls-files").splitlines():
        if Path(chemin).name == ".env":
            problemes.append(f"Le fichier {chemin} est suivi par Git (il doit être dans .gitignore).")
    historique_env = _git(racine, "log", "--all", "--format=%h", "--", ".env", "**/.env").split()
    for commit in historique_env:
        problemes.append(f"Un fichier .env a déjà été commité (commit {commit}).")

    # 2. Les vraies valeurs secrètes du .env local dans l'historique ou dans .env.example
    for nom, valeur in _valeurs_sensibles_du_env(racine).items():
        commits = _git(racine, "log", "--all", "--format=%h", "-S", valeur).split()
        if commits:
            problemes.append(
                f"La valeur de {nom} apparaît dans {len(commits)} commit(s) (ex. {commits[0]}) : "
                "changez ce secret, le supprimer du dépôt ne suffit pas."
            )
        exemple = Path(racine) / ".env.example"
        if exemple.exists() and valeur in exemple.read_text(encoding="utf-8", errors="replace"):
            problemes.append(f"La valeur de {nom} figure dans .env.example (qui est commité).")

    # 3. Motifs suspects dans les lignes ajoutées (hors tests/)
    commit_courant = fichier_courant = None
    sortie = _git(racine, "log", "--all", "-p", "--no-color", "--format=COMMIT %h", "--", ".", ":!tests")
    for ligne in sortie.splitlines():
        if ligne.startswith("COMMIT "):
            commit_courant = ligne.split()[1]
        elif ligne.startswith("+++ b/"):
            fichier_courant = ligne[6:]
        elif ligne.startswith("+") and not ligne.startswith("+++"):
            for motif, groupe in ((MOTIF_AFFECTATION, 2), (MOTIF_URL_AVEC_MOT_DE_PASSE, 2)):
                for trouve in motif.finditer(ligne):
                    if not _est_un_exemple(trouve.group(groupe)):
                        problemes.append(
                            f"Motif suspect (valeur masquée) dans {fichier_courant}, commit {commit_courant}."
                        )
    return sorted(set(problemes))


def main():
    racine = Path(__file__).resolve().parent.parent
    if not (racine / ".git").exists():
        print("Ce dossier n'est pas un dépôt Git.")
        return 1
    if not (racine / ".env").exists():
        print("Note : pas de fichier .env local, la vérification des valeurs secrètes est ignorée.")
    problemes = auditer(racine)
    if not problemes:
        print("Audit OK : aucun secret détecté dans l'historique Git (toutes branches).")
        return 0
    print("PROBLÈMES TROUVÉS :")
    for probleme in problemes:
        print(f" - {probleme}")
    return 1


if __name__ == "__main__":
    sys.exit(main())