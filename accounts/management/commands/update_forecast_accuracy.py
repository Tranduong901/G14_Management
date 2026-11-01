from django.core.management.base import BaseCommand

from dss.services import get_closed_forecast_results, update_forecast_accuracy


class Command(BaseCommand):
    help = 'Updates actual quantity and error rate for forecast results.'

    def handle(self, *args, **options):
        updated = 0
        for result in get_closed_forecast_results():
            update_forecast_accuracy(result)
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} forecast results.'))
