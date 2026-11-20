from app.extensions import db


class DimCommune(db.Model):
    __tablename__ = "Dim_Commune"

    id_commune = db.Column(db.Integer, primary_key=True)
    code_insee = db.Column(db.String(5), nullable=False, unique=True)
    nom_commune = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Numeric(8, 5), nullable=False)
    longitude = db.Column(db.Numeric(8, 5), nullable=False)
    altitude_m = db.Column(db.SmallInteger)
    zone_climatique = db.Column(db.String(50))
    remarque_agricole = db.Column(db.String(150))

    def __repr__(self):
        return f"<DimCommune {self.nom_commune}>"