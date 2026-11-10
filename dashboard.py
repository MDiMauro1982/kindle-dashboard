"""
Dashboard per Kindle Paperwhite 7 (1072x1448): data, meteo di due città e agenda Google Calendar.
Genera il file dash.png. Pensato per girare su GitHub Actions.
"""
import os
import datetime as dt
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

# ================== IMPOSTAZIONI (puoi modificarle) ==================
CITTA = [
    {"nome": "Lesmo", "lat": 45.6466, "lon": 9.3073},
    {"nome": "Rosolini", "lat": 36.8197, "lon": 14.9478},
]
GIORNI_AGENDA = 7          # quanti giorni di appuntamenti mostrare
MOSTRA_TITOLI = True       # False = mostra "Impegno" al posto del titolo (più privacy)
# ====================================================================

TZ = ZoneInfo("Europe/Rome")
W, H = 1072, 1448
NERO, GRIGIO, GRIGIO_CHIARO, BIANCO = 0, 90, 170, 255
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
GIORNI_BREVI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

METEO_TESTO = {
    0: "Sereno", 1: "Prevalentemente sereno", 2: "Parzialmente nuvoloso", 3: "Coperto",
    45: "Nebbia", 48: "Nebbia", 51: "Pioviggine", 53: "Pioviggine", 55: "Pioviggine",
    56: "Pioviggine gelata", 57: "Pioviggine gelata", 61: "Pioggia debole", 63: "Pioggia",
    65: "Pioggia forte", 66: "Pioggia gelata", 67: "Pioggia gelata", 71: "Neve debole",
    73: "Neve", 75: "Neve forte", 77: "Nevischio", 80: "Rovesci deboli", 81: "Rovesci",
    82: "Rovesci forti", 85: "Rovesci di neve", 86: "Rovesci di neve", 95: "Temporale",
    96: "Temporale con grandine", 99: "Temporale con grandine",
}


def font(size, bold=False):
    nome = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(FONT_DIR + nome, size)


def tronca(draw, testo, fnt, larghezza):
    if draw.textlength(testo, font=fnt) <= larghezza:
        return testo
    while testo and draw.textlength(testo + "…", font=fnt) > larghezza:
        testo = testo[:-1]
    return testo + "…"


# ------------------------- ICONE METEO -------------------------
def categoria(code):
    if code in (0, 1): return "sole"
    if code == 2: return "parziale"
    if code == 3: return "nuvola"
    if code in (45, 48): return "nebbia"
    if code in (71, 73, 75, 77, 85, 86): return "neve"
    if code in (95, 96, 99): return "temporale"
    return "pioggia"


def sole(d, cx, cy, r):
    import math
    for i in range(8):
        a = i * math.pi / 4
        d.line([(cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35),
                (cx + math.cos(a) * r * 1.8, cy + math.sin(a) * r * 1.8)],
               fill=NERO, width=max(2, int(r / 5)))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NERO)


def nuvola(d, cx, cy, s, colore=GRIGIO):
    contorno = max(2, int(s / 25))
    pezzi = [
        (cx - s * 0.45, cy - s * 0.05, s * 0.28),
        (cx - s * 0.1, cy - s * 0.22, s * 0.36),
        (cx + s * 0.3, cy - s * 0.02, s * 0.27),
    ]
    # prima il contorno nero, poi il riempimento: forma unica e pulita
    for fill, extra in ((NERO, contorno), (colore, 0)):
        for x, y, r in pezzi:
            d.ellipse([x - r - extra, y - r - extra, x + r + extra, y + r + extra], fill=fill)
        d.rounded_rectangle([cx - s * 0.6 - extra, cy - s * 0.05 - extra,
                             cx + s * 0.55 + extra, cy + s * 0.25 + extra],
                            radius=s * 0.15, fill=fill)


def icona(d, cx, cy, size, code):
    c = categoria(code)
    s = size
    if c == "sole":
        sole(d, cx, cy, s * 0.25)
    elif c == "parziale":
        sole(d, cx + s * 0.18, cy - s * 0.18, s * 0.17)
        nuvola(d, cx - s * 0.05, cy + s * 0.08, s * 0.85, colore=BIANCO)
    elif c == "nuvola":
        nuvola(d, cx, cy, s)
    elif c == "nebbia":
        for i in range(4):
            y = cy - s * 0.3 + i * s * 0.2
            d.line([(cx - s * 0.45, y), (cx + s * 0.45, y)], fill=NERO, width=max(3, int(s / 14)))
    else:
        nuvola(d, cx, cy - s * 0.15, s * 0.9)
        base = cy + s * 0.2
        if c == "pioggia":
            for i in range(3):
                x = cx - s * 0.25 + i * s * 0.25
                d.line([(x, base), (x - s * 0.08, base + s * 0.25)], fill=NERO, width=max(3, int(s / 14)))
        elif c == "neve":
            for i in range(3):
                x = cx - s * 0.25 + i * s * 0.25
                r = s * 0.05
                d.ellipse([x - r, base + s * 0.12 - r, x + r, base + s * 0.12 + r], fill=NERO)
        elif c == "temporale":
            d.polygon([(cx + s * 0.05, base - s * 0.02), (cx - s * 0.12, base + s * 0.18),
                       (cx, base + s * 0.18), (cx - s * 0.08, base + s * 0.35),
                       (cx + s * 0.15, base + s * 0.1), (cx + s * 0.02, base + s * 0.1)], fill=NERO)


# ------------------------- DATI -------------------------
def meteo(citta):
    if os.environ.get("DEMO"):
        return {"temp": 14.3, "code": 2, "giorni": [
            {"data": dt.date.today() + dt.timedelta(days=i), "code": c, "max": 16 - i, "min": 8 - i, "pioggia": p}
            for i, (c, p) in enumerate([(2, 10), (61, 70), (3, 30), (0, 0)])]}
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": citta["lat"], "longitude": citta["lon"],
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Europe/Rome", "forecast_days": 4,
    }, timeout=30)
    r.raise_for_status()
    j = r.json()
    giorni = []
    dd = j["daily"]
    for i in range(len(dd["time"])):
        giorni.append({
            "data": dt.date.fromisoformat(dd["time"][i]),
            "code": dd["weather_code"][i],
            "max": dd["temperature_2m_max"][i],
            "min": dd["temperature_2m_min"][i],
            "pioggia": dd["precipitation_probability_max"][i] or 0,
        })
    return {"temp": j["current"]["temperature_2m"], "code": j["current"]["weather_code"], "giorni": giorni}


def eventi(oggi):
    if os.environ.get("DEMO"):
        return [
            (oggi, 0, "", "Compleanno di Marco"),
            (oggi, 1, "09:30", "Riunione di lavoro con il team"),
            (oggi, 1, "18:00", "Palestra"),
            (oggi + dt.timedelta(days=1), 1, "12:30", "Pranzo con Giulia"),
            (oggi + dt.timedelta(days=3), 1, "10:00", "Dentista"),
        ]
    import icalendar
    import recurring_ical_events

    url = os.environ.get("ICS_URL", "").strip()
    if not url:
        raise RuntimeError("ICS_URL mancante")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    cal = icalendar.Calendar.from_ical(r.content)
    inizio = dt.datetime.combine(oggi, dt.time(), TZ)
    fine = inizio + dt.timedelta(days=GIORNI_AGENDA)
    lista = []
    for e in recurring_ical_events.of(cal).between(inizio, fine):
        s = e["DTSTART"].dt
        titolo = str(e.get("SUMMARY", "(senza titolo)")) if MOSTRA_TITOLI else "Impegno"
        if isinstance(s, dt.datetime):
            if s.tzinfo is None:
                s = s.replace(tzinfo=TZ)
            s = s.astimezone(TZ)
            if s.date() < oggi:
                lista.append((oggi, 1, "in corso", titolo))
            else:
                lista.append((s.date(), 1, s.strftime("%H:%M"), titolo))
        else:  # evento di tutta la giornata
            lista.append((max(s, oggi), 0, "", titolo))
    lista.sort(key=lambda x: (x[0], x[1], x[2]))
    return lista


# ------------------------- DISEGNO -------------------------
def disegna_meteo(d, x0, y0, larghezza, citta):
    pad = 36
    d.text((x0 + pad, y0), citta["nome"], font=font(40, True), fill=NERO)
    try:
        m = meteo(citta)
    except Exception as ex:
        print("Errore meteo", citta["nome"], ex)
        d.text((x0 + pad, y0 + 80), "Meteo non disponibile", font=font(28), fill=GRIGIO)
        return
    icona(d, x0 + pad + 70, y0 + 150, 130, m["code"])
    d.text((x0 + pad + 170, y0 + 95), f"{round(m['temp'])}°", font=font(96, True), fill=NERO)
    oggi = m["giorni"][0]
    d.text((x0 + pad, y0 + 240), tronca(d, METEO_TESTO.get(m["code"], ""), font(28), larghezza - 2 * pad),
           font=font(28), fill=NERO)
    d.text((x0 + pad, y0 + 282), f"Min {round(oggi['min'])}°   Max {round(oggi['max'])}°   Pioggia {oggi['pioggia']}%",
           font=font(24), fill=GRIGIO)
    # prossimi 3 giorni
    col = (larghezza - 2 * pad) / 3
    for i, g in enumerate(m["giorni"][1:4]):
        cx = x0 + pad + col * i + col / 2
        nome = GIORNI_BREVI[g["data"].weekday()]
        d.text((cx, y0 + 345), nome, font=font(28, True), fill=NERO, anchor="mm")
        icona(d, cx, y0 + 410, 64, g["code"])
        d.text((cx, y0 + 470), f"{round(g['max'])}° / {round(g['min'])}°", font=font(24), fill=NERO, anchor="mm")


def etichetta_giorno(g, oggi):
    if g == oggi:
        return "Oggi"
    if g == oggi + dt.timedelta(days=1):
        return "Domani"
    return f"{GIORNI[g.weekday()]} {g.day} {MESI[g.month - 1]}"


def disegna_agenda(d, y, oggi):
    d.text((40, y), "Prossimi impegni", font=font(42, True), fill=NERO)
    y += 70
    limite = H - 80
    try:
        lista = eventi(oggi)
    except Exception as ex:
        print("Errore calendario:", ex)
        d.text((40, y), "Calendario non disponibile", font=font(30), fill=GRIGIO)
        return
    if not lista:
        d.text((40, y), f"Nessun impegno nei prossimi {GIORNI_AGENDA} giorni", font=font(30), fill=GRIGIO)
        return
    f_giorno, f_ora, f_tit = font(32, True), font(28, True), font(30)
    giorno_corrente = None
    for idx, (g, _, ora, titolo) in enumerate(lista):
        serve = 44 + (64 if g != giorno_corrente else 0)
        if y + serve > limite:
            rimasti = len(lista) - idx
            d.text((40, y + 4), f"+ altri {rimasti} impegni", font=font(26), fill=GRIGIO)
            break
        if g != giorno_corrente:
            giorno_corrente = g
            y += 8
            if g == oggi:
                d.rectangle([40, y, 40 + d.textlength("Oggi", font=f_giorno) + 28, y + 46], fill=NERO)
                d.text((54, y + 4), "Oggi", font=f_giorno, fill=BIANCO)
            else:
                d.text((40, y + 4), etichetta_giorno(g, oggi), font=f_giorno, fill=NERO)
            y += 56
        d.text((60, y), ora if ora else "Tutto il giorno", font=f_ora if ora else font(24), fill=GRIGIO if not ora else NERO)
        d.text((290, y), tronca(d, titolo, f_tit, W - 290 - 40), font=f_tit, fill=NERO)
        y += 44


def main():
    ora = dt.datetime.now(TZ)
    oggi = ora.date()
    img = Image.new("L", (W, H), BIANCO)
    d = ImageDraw.Draw(img)

    # intestazione
    d.text((40, 30), f"{GIORNI[oggi.weekday()]} {oggi.day} {MESI[oggi.month - 1]}", font=font(70, True), fill=NERO)
    d.text((40, 118), str(oggi.year), font=font(30), fill=GRIGIO)
    d.line([(40, 170), (W - 40, 170)], fill=NERO, width=3)

    # meteo su due colonne
    y_meteo = 195
    meta = W // 2
    for i, c in enumerate(CITTA[:2]):
        disegna_meteo(d, i * meta, y_meteo, meta, c)
    d.line([(meta, y_meteo + 10), (meta, y_meteo + 490)], fill=GRIGIO_CHIARO, width=2)
    d.line([(40, 715), (W - 40, 715)], fill=NERO, width=3)

    # agenda
    disegna_agenda(d, 740, oggi)

    # piè di pagina
    d.text((W - 40, H - 30), f"Aggiornato alle {ora.strftime('%H:%M')}", font=font(24), fill=GRIGIO, anchor="rm")

    img.save("dash.png")
    print("Creato dash.png")


if __name__ == "__main__":
    main()
