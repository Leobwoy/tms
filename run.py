# run.py
from app import create_app, db
from app.tms.models import Carrier

app = create_app()

# Automatically seed carriers if none exist
with app.app_context():
    if Carrier.query.first() is None:
        carrier1 = Carrier(name="FastTrans", cost_factor=1.0)
        carrier2 = Carrier(name="EcoMove", cost_factor=0.8)
        db.session.add_all([carrier1, carrier2])
        db.session.commit()
        print("Default carriers added to the database.")

if __name__ == '__main__':
    app.run(debug=True)

