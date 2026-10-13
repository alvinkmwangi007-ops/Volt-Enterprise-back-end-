import os
import re
import sys

from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from database import get_session
from Models import User, UserRole


def main():
    full_name = os.getenv("MANAGER_NAME", "Alvin").strip()
    email = os.getenv("MANAGER_EMAIL", "alvink.mwangi007@gmail.com").strip().lower()
    phone_number = os.getenv("MANAGER_PHONE", "+254702710404").strip()
    if phone_number.startswith("0") and len(phone_number) == 10:
        phone_number = f"+254{phone_number[1:]}"
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone_number):
        raise SystemExit("Enter a valid phone number in E.164 format.")
    password = os.getenv("MANAGER_INITIAL_PASSWORD")
    if not password or len(password) < 12:
        raise SystemExit("Set MANAGER_INITIAL_PASSWORD to a password of at least 12 characters.")

    app = create_app("development")
    with app.app_context():
        db = get_session()
        try:
            existing = db.query(User).filter(
                (User.email == email) | (User.phone_number == phone_number)
            ).first()
            if existing:
                if existing.email != email or existing.phone_number != phone_number:
                    raise SystemExit("The requested email or phone number is already assigned to another account.")
                existing.full_name = full_name
                existing.password_hash = generate_password_hash(password)
                existing.role = UserRole.manager
                existing.is_verified = True
            else:
                manager = User(
                    full_name=full_name,
                    email=email,
                    phone_number=phone_number,
                    password_hash=generate_password_hash(password),
                    role=UserRole.manager,
                    is_verified=True,
                )
                db.add(manager)
            db.commit()
            print("Manager account created. Sign in through the Manager login screen.")
        finally:
            db.close()


if __name__ == "__main__":
    main()
