from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from firma_db import fetch_artikel_top10, fetch_artikel_by_nr # <-- importiere Funktion

def test_firma_view(request):
    data = fetch_artikel_top10()

    # pyodbc Rows → in Python-Listen umbauen
    #data = [list(row) for row in rows]

    return JsonResponse({"artikel": data})


def artikel_nr_view(request):
    art_nr = request.GET.get("nr")  # z.B. ?nr=MTL0010

    if not art_nr:
        return JsonResponse({"error": "Bitte Artikelnummer mit ?nr= eingeben."})

    result = fetch_artikel_by_nr(art_nr)

    if result is None:
        return JsonResponse({"error": "Artikel nicht gefunden."})

    return JsonResponse({"artikel": result})