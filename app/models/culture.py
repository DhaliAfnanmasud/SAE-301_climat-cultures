from app.extensions import db


class DimCulture(db.Model):
    __tablename__ = "Dim_Culture"

    id_culture = db.Column(db.Integer, primary_key=True)
    nom_culture = db.Column(db.String(50), nullable=False)
    temperature_base = db.Column(db.Numeric(4, 1), nullable=False)
    gdd_maturite = db.Column(db.Integer)
    seuil_gel = db.Column(db.Numeric(4, 1), nullable=False)
    stade_gel_reference = db.Column(db.String(100))
    seuil_stress_thermique = db.Column(db.Numeric(4, 1))
    temperature_optimale_min = db.Column(db.Numeric(4, 1))
    temperature_optimale_max = db.Column(db.Numeric(4, 1))
    besoin_eau_min_mm = db.Column(db.SmallInteger)
    besoin_eau_max_mm = db.Column(db.SmallInteger)
    ordre_priorite_mvp = db.Column(db.SmallInteger)

    def __repr__(self):
        return f"<DimCulture {self.nom_culture}>"