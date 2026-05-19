from app import app
from database import db, User

with app.app_context():
    user = User.query.first()
    user.linkedin_url = "https://www.linkedin.com/in/manikanta-saikumar-poola-6436a1260/"
    user.github_url = "https://github.com/Manikantapoola"
    user.notify_email = "Manikantapoola.03@gmail.com"
    db.session.commit()
    print("Updated:", user.full_name)
    print("LinkedIn:", user.linkedin_url)
    print("GitHub:", user.github_url)
    print("Notify:", user.notify_email)
    print("Done!")