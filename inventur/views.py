from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse, HttpResponse
from firma_db import fetch_artikel_lager # <-- importiere Funktion

def test_firma_view(request):
    data = fetch_artikel_lager()
    return JsonResponse({"artikel": data}, safe=False)


def startseite(request):
    return HttpResponse("Hallo, das ist die Startseite der Inventur-App 🙂")

def lager_artikel_view(request):
    count, anzahl_wg, unique_wg, gruppen, uebergruppen = fetch_artikel_lager()
    return render(request, "lager_artikel.html", {
        "count": count,
        "group": anzahl_wg,
        "unique_wg": unique_wg,
        "uebergruppen": uebergruppen,
    })