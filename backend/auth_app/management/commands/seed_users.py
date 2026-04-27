import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Seed users from APP_PASSWORD env var (comma-separated). First = admin.'

    def handle(self, *args, **options):
        raw = os.environ.get('APP_PASSWORD', 'cpseisawesome')
        passwords = [p.strip() for p in raw.split(',') if p.strip()]

        if not passwords:
            self.stderr.write("APP_PASSWORD is empty — no users created.")
            return

        for idx, password in enumerate(passwords):
            username = 'admin' if idx == 0 else f'viewer{idx}'
            is_staff = idx == 0

            if User.objects.filter(username=username).exists():
                self.stdout.write(f"User '{username}' already exists — skipping.")
                continue

            User.objects.create_user(
                username=username, password=password, is_staff=is_staff
            )
            role = 'admin' if is_staff else 'viewer'
            self.stdout.write(
                self.style.SUCCESS(f"Created {role} user: '{username}'")
            )
