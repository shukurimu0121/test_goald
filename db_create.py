from app import app, db
# Create the database and the db table
with app.app_context():
    db.create_all()