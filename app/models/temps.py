from app.extensions import db


class DimTemps(db.Model):
    __tablename__ = "Dim_Temps"

    id_temps = db.Column(db.Integer, primary_key=True)
    horizon = db.Column(db.String(20), nullable=False)
    annee_debut = db.Column(db.SmallInteger, nullable=False)
    annee_fin = db.Column(db.SmallInteger, nullable=False)
    saison = db.Column(db.String(20))

    def __repr__(self):
        return f"<DimTemps {self.horizon}>"