from django.db import models

class Inventur(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="RUNNING")
    stichtag = models.DateField(null=True, blank=True)
    created_at = models.DateField()

class InventurPosition(models.Model):
    inventur_id = models.ForeignKey(Inventur, on_delete=models.CASCADE)
    Cortexnr = models.IntegerField(primary_key=True)
    Hersteller = models.CharField(max_length=200)
    Artikelnr_Hersteller = models.CharField(max_length=100)
    Artikelnaam = models.CharField(max_length=200)
    Verpackungseinheit = models.FloatField()
    Anzahl = models.IntegerField()
    Einheit_Rest = models.FloatField()
    Anazahl = models.IntegerField()
    ART_ART_NR = models.CharField(max_length=100)
    EK = models.FloatField()
    WOG_NAME = models.CharField(max_length=50)
    WOG_NR = models.IntegerField()
    WG_NAME = models.CharField(max_length=50)
    WG_NR = models.IntegerField()
    EINHEIT = models.CharField(max_length=10)
    EINH_UMR = models.FloatField()


# Create your models here.
