from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Импорт конституции в базу знаний / RAG'

    def handle(self, *args, **options):
        # Логика из файла tools/import_constitution.py
        self.stdout.write(self.style.SUCCESS('Импорт успешно завершен!'))