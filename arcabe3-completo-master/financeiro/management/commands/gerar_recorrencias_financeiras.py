from django.core.management.base import BaseCommand

from financeiro.services import generate_recurring


class Command(BaseCommand):
    help = 'Gera lançamentos recorrentes mensais do módulo financeiro.'

    def handle(self, *args, **options):
        created = generate_recurring()
        self.stdout.write(self.style.SUCCESS(f'{created} recorrências geradas.'))
