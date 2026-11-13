"""Create or update a staff account (admin by default).

Usage (inside the running container):
    docker compose exec -it api python scripts/provision_admin.py

Values can also be supplied via ADMIN_NAME, ADMIN_EMAIL, ADMIN_PHONE and
ADMIN_INITIAL_PASSWORD; anything missing is prompted for.
"""

import getpass
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


def ask(env_name, prompt, secret=False):
    value = os.getenv(env_name)
    if value:
        return value.strip() if not secret else value
    return getpass.getpass(prompt) if secret else input(prompt).strip()


def main():
    full_name = ask("ADMIN_NAME", "Full name: ")
    email = ask("ADMIN_EMAIL", "Email: ").lower()
    phone_number = ask("ADMIN_PHONE", "Phone (E.164, e.g. +2547XXXXXXXX): ")
    if phone_number.startswith("0") and len(phone_number) == 10:
        phone_number = f"+254{phone_number[1:]}"
    if not full_name or "@" not in email:
        raise SystemExit("A name and a valid email are required.")
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone_number):
        raise SystemExit("Enter a valid phone number in E.164 format.")
    password = ask("ADMIN_INITIAL_PASSWORD", "Password (min 12 chars): ", secret=True)
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")

    role = UserRole.admin
    app = create_app(os.getenv("FLASK_ENV", "production"))
    with app.app_context():
        db = get_session()
        try:
            existing = db.query(User).filter(
                (User.email == email) | (User.phone_number == phone_number)
            ).first()
            if existing:
                if existing.email != email or existing.phone_number != phone_number:
                    raise SystemExit("That email or phone number belongs to another account.")
                existing.full_name = full_name
                existing.password_hash = generate_password_hash(password)
                existing.role = role
                existing.is_verified = True
            else:
                db.add(User(
                    full_name=full_name,
                    email=email,
                    phone_number=phone_number,
                    password_hash=generate_password_hash(password),
                    role=role,
                    is_verified=True,
                ))
            db.commit()
            print("Admin account ready. Sign in via 'Admin Login' on the site.")
        finally:
            db.close()


if __name__ == "__main__":
    main()
