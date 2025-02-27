from app import db
from app.tms.models import User

username = input("Enter the username to promote to admin: ")

user = User.query.filter_by(username=username).first()
if user:
    user.role = 'admin'
    db.session.commit()
    print(f"User '{user.username}' has been promoted to admin.")
else:
    print("User not found.")
