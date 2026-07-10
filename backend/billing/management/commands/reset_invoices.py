from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import AccountingEntry, Invoice, InvoiceLine, Payment


class Command(BaseCommand):
    help = "Remet à zéro le registre des factures (paiements, écritures liées, lignes, factures)."

    def handle(self, *args, **options):
        with transaction.atomic():
            payments = Payment.objects.count()
            entries = AccountingEntry.objects.filter(invoice__isnull=False).count()
            lines = InvoiceLine.objects.count()
            invoices = Invoice.objects.count()

            Payment.objects.all().delete()
            AccountingEntry.objects.filter(invoice__isnull=False).delete()
            InvoiceLine.objects.all().delete()
            Invoice.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Registre factures réinitialisé : {invoices} facture(s), "
                f"{lines} ligne(s), {payments} paiement(s), {entries} écriture(s) supprimé(s)."
            )
        )
