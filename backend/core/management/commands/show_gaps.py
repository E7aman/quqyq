"""python manage.py show_gaps — вопросы без ответа в базе (нужен LOG_GAPS=1 при работе сервера)."""
from django.core.management.base import BaseCommand

from core import gaps


class Command(BaseCommand):
    help = "Показывает самые частые вопросы, на которые бот ответил отказом: что добавить в базу знаний."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=30)

    def handle(self, *args, **opts):
        rows = gaps.top_gaps(opts["limit"])
        if not rows:
            self.stdout.write("Журнал пуст. Запустите сервер с LOG_GAPS=1 и задайте вопросы.")
            return
        for q, n in rows:
            self.stdout.write(f"{n:>3}  {q}")
