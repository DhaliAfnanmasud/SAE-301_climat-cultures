from app.extensions import db

# Classe qui charge la table Modèle dans la base de données
class DimModele(db.Model):
    __tablename__ = "Dim_Modele"

    id_modele = db.Column(db.Integer, primary_key=True)
    code_api = db.Column(db.String(30), nullable=False)
    nom_complet = db.Column(db.String(100))
    origine = db.Column(db.String(100))

    def __repr__(self):
        return f"<DimModele {self.code_api}>"