from django.db import models

class Inventur(models.Model):
    name = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    created_at = models.DateField()

class InventurPosition(models.Model):
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
    date = models.DateField()

# Create your models here.
