from django.db import models

class artikel(models.Model):
    CORTEXNR = models.IntegerField(primary_key=True)
    HERST_NAME = models.CharField(max_length=200)
    HERST_ART_NR = models.CharField(max_length=100)
    ART_NAME = models.CharField(max_length=200)
    VERPACKUNGSEINHEIT = models.FloatField()
    ANZAHL = models.IntegerField()
    EINHEIT_REST = models.FloatField()
    ANZAHLZ = models.IntegerField()
    ART_ART_NR = models.CharField(max_length=100)
    EK = models.FloatField()
    WOG_NAME = models.CharField(max_length=50)
    WOG_NR = models.IntegerField()
    WG_NAME = models.CharField(max_length=50)
    WG_NR = models.IntegerField()
    EINHEIT = models.CharField(max_length=10)
    EINH_UMR = models.FloatField()


class InventurArtikel(models.Model):
    cortexnr = models.CharField(max_length=50)
    hersteller = models.CharField(max_length=200)
    herst_art_nr = models.CharField(max_length=100, blank=True)
    artikelname = models.CharField(max_length=300)

    wg_name = models.CharField(max_length=100)
    wog_nr = models.IntegerField()

    einheit = models.CharField(max_length=20)
    einh_umr = models.FloatField(null=True, blank=True)

    ek = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    # Meta
    erstellt_am = models.DateTimeField(auto_now_add=True)
# Create your models here.
