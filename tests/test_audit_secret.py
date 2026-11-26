import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from scripts.audit_secrets import auditer 


def _git(dossier, *arguments):
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *arguments],
        cwd=dossier, check=True, capture_output=True,
    )


def _depot(dossier, fichiers):
    """Petit dépôt Git jetable avec un premier commit."""
    dossier.mkdir(exist_ok=True)
    _git(dossier, "init", "-q")
    for nom, contenu in fichiers.items():
        (dossier / nom).write_text(contenu, encoding="utf-8")
        _git(dossier, "add", nom)
    _git(dossier, "commit", "-q", "-m", "premier commit")
    return dossier


def test_depot_propre_sans_probleme(tmp_path):
    depot = _depot(tmp_path / "depot", {"app.py": "print('bonjour')\n", ".gitignore": ".env\n"})
    (depot / ".env").write_text("DB_PASSWORD=Sup3rS3cret!\n", encoding="utf-8")  # non suivi

    assert auditer(depot) == []


def test_env_suivi_par_git_est_detecte(tmp_path):
    depot = _depot(tmp_path / "depot", {".env": "DB_PASSWORD=Sup3rS3cret!\n"})

    problemes = auditer(depot)

    assert any("suivi par Git" in p for p in problemes)


def test_mot_de_passe_commite_puis_supprime_reste_detecte_sans_etre_affiche(tmp_path):
    depot = _depot(tmp_path / "depot", {"config.txt": "DB_PASSWORD=Sup3rS3cret!\n"})
    _git(depot, "rm", "-q", "config.txt")
    _git(depot, "commit", "-q", "-m", "suppression")
    (depot / ".env").write_text("DB_PASSWORD=Sup3rS3cret!\n", encoding="utf-8")

    problemes = auditer(depot)

    assert any("DB_PASSWORD" in p and "changez ce secret" in p for p in problemes)
    assert all("Sup3rS3cret" not in p for p in problemes)  # la valeur n'est jamais affichée


def test_motif_suspect_dans_le_code_est_detecte_et_masque(tmp_path):
    depot = _depot(tmp_path / "depot", {"app.py": 'mot_de_passe = "Azerty987654"\n'})

    problemes = auditer(depot)

    assert any("Motif suspect" in p and "app.py" in p for p in problemes)
    assert all("Azerty" not in p for p in problemes)


def test_valeur_d_exemple_et_dossier_tests_ignores(tmp_path):
    dossier = tmp_path / "depot"
    dossier.mkdir()
    _git(dossier, "init", "-q")
    (dossier / "app.py").write_text('SECRET_KEY = "cle-secrete-dev"\n', encoding="utf-8")
    (dossier / "tests").mkdir()
    (dossier / "tests" / "test_x.py").write_text('mot_de_passe = "Motdepasse123"\n', encoding="utf-8")
    _git(dossier, "add", ".")
    _git(dossier, "commit", "-q", "-m", "exemples")

    assert auditer(dossier) == []


def test_valeur_du_env_dans_env_example_est_detectee(tmp_path):
    depot = _depot(tmp_path / "depot", {".env.example": "DB_PASSWORD=Sup3rS3cret!\n", ".gitignore": ".env\n"})
    (depot / ".env").write_text("DB_PASSWORD=Sup3rS3cret!\n", encoding="utf-8")

    problemes = auditer(depot)

    assert any(".env.example" in p for p in problemes)


def test_marqueurs_de_remplacement_en_majuscules_ignores(tmp_path):
    exemple = "# DATABASE_URL=mysql+pymysql://UTILISATEUR:MOT_DE_PASSE@hote/base\n"
    depot = _depot(tmp_path / "depot", {".env.example": exemple})

    assert auditer(depot) == []