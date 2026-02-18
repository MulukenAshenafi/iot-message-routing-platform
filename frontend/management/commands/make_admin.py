"""
Management command to make a user an admin
Usage: python manage.py make_admin <email_or_username>
"""
from django.core.management.base import BaseCommand
from accounts.models import Owner


class Command(BaseCommand):
    help = 'Make a user an admin (is_staff=True, is_superuser=True)'

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            type=str,
            help='Email or username of the user to make admin'
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        
        try:
            # Try to find user by email first
            if '@' in identifier:
                user = Owner.objects.get(email=identifier)
            else:
                # Try by username
                user = Owner.objects.get(username=identifier)
            
            # Make user admin
            user.is_staff = True
            user.is_superuser = True
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully made {user.email} ({user.username}) an admin user.'
                )
            )
            self.stdout.write(f'  - Email: {user.email}')
            self.stdout.write(f'  - Username: {user.username}')
            self.stdout.write(f'  - is_staff: {user.is_staff}')
            self.stdout.write(f'  - is_superuser: {user.is_superuser}')
            
        except Owner.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'User with email/username "{identifier}" not found.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )

