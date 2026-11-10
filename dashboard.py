"""
Dashboard per Kindle Paperwhite 7 (1072x1448).
Genera tre viste (giorno, settimana, mese) e copia quella scelta in dash.png.
La vista si sceglie con la variabile VISTA su GitHub: giorno, settimana, mese oppure auto.
Il secret ICS_URL può contenere più indirizzi di calendario, uno per riga.
"""
import os
import calendar
import datetime as dt
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

# ================== IMPOSTAZIONI (puoi modificarle) ==================
CITTA = [
    {"nome": "Lesmo", "lat": 45.6466, "lon": 9.3073},
    {"nome": "Rosolini", "lat": 36.8197, "lon": 14.9478},
]
VISTA_PREDEFINITA = "settimana"   # usata se su GitHub non imposti la variabile VISTA
MOSTRA_TITOLI = True              # False = mostra "Impegno" al posto del titolo (più privacy)

# Con VISTA = auto: dall'ora indicata in poi si usa quella vista (ora italiana)
VISTE_AUTOMATICHE = [(6, "giorno"), (12, "settimana"), (18, "mese")]

# Raccolta differenziata: cosa passa a ritirare ogni giorno (0 = lunedì ... 6 = domenica).
# Esempio: {0: "Umido", 2: "Plastica", 4: "Carta e umido"}. Lascia {} per non mostrarla.
RACCOLTA = {2: "Umido & secco", 3: "Plastica & Carta", 5: "Umido & Vetro"}

# Avvisi meteo calcolati dalle previsioni (non sono allerte ufficiali della Protezione Civile)
SOGLIA_RAFFICHE_KMH = 60
SOGLIA_PIOGGIA_MM = 30
SOGLIA_CALDO = 35
SOGLIA_GELO = -2

# Frase del giorno: cambia ogni giorno. Puoi aggiungere o togliere frasi a piacere.
FRASI = [
    "Chi va piano va sano e va lontano.",
    "Chi ben comincia è a metà dell'opera.",
    "Il mattino ha l'oro in bocca.",
    "Non rimandare a domani quello che puoi fare oggi.",
    "Chi trova un amico trova un tesoro.",
    "Tra il dire e il fare c'è di mezzo il mare.",
    "Meglio tardi che mai.",
    "A buon intenditor poche parole.",
    "Rosso di sera, bel tempo si spera.",
    "Una mela al giorno toglie il medico di torno.",
    "Chi dorme non piglia pesci.",
    "Volere è potere.",
    "L'appetito vien mangiando.",
    "Chi la dura la vince.",
    "Sbagliando s'impara.",
    "Paese che vai, usanza che trovi.",
    "Non tutte le ciambelle riescono col buco.",
    "Chi fa da sé fa per tre.",
    "Il tempo è galantuomo.",
    "Chi cerca trova.",
    "Chi ha tempo non aspetti tempo.",
    "Le bugie hanno le gambe corte.",
    "Ride bene chi ride ultimo.",
    "Il buon giorno si vede dal mattino.",
    "Chi si contenta gode.",
    "Dopo la tempesta viene il sereno.",
    "Fidarsi è bene, non fidarsi è meglio.",
    "Non è tutto oro quello che luccica.",
    "L'unione fa la forza.",
    "Tutto è bene quel che finisce bene.",
    "Natale con i tuoi, Pasqua con chi vuoi.",
]
# ====================================================================

LIMITE = 1448 - 185   # da qui in giù c'è la barra informazioni

TZ = ZoneInfo("Europe/Rome")
W, H = 1072, 1448
NERO, GRIGIO, GRIGIO_CHIARO, BIANCO = 0, 90, 190, 255
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

_font_cache = {}


def font(size, bold=False, corsivo=False):
    k = (size, bold, corsivo)
    if k not in _font_cache:
        nome = "DejaVuSans" + ("-Bold" if bold else "") + ("Oblique" if corsivo and bold else "-Oblique" if corsivo else "") + ".ttf"
        _font_cache[k] = ImageFont.truetype(FONT_DIR + nome, size)
    return _font_cache[k]


def tronca(d, testo, fnt, larghezza):
    if d.textlength(testo, font=fnt) <= larghezza:
        return testo
    while testo and d.textlength(testo + "…", font=fnt) > larghezza:
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
    pezzi = [(cx - s * 0.45, cy - s * 0.05, s * 0.28),
             (cx - s * 0.1, cy - s * 0.22, s * 0.36),
             (cx + s * 0.3, cy - s * 0.02, s * 0.27)]
    for fill, extra in ((NERO, contorno), (colore, 0)):
        for x, y, r in pezzi:
            d.ellipse([x - r - extra, y - r - extra, x + r + extra, y + r + extra], fill=fill)
        d.rounded_rectangle([cx - s * 0.6 - extra, cy - s * 0.05 - extra,
                             cx + s * 0.55 + extra, cy + s * 0.25 + extra],
                            radius=s * 0.15, fill=fill)


def icona(d, cx, cy, s, code):
    c = categoria(code)
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
        else:
            d.polygon([(cx + s * 0.05, base - s * 0.02), (cx - s * 0.12, base + s * 0.18),
                       (cx, base + s * 0.18), (cx - s * 0.08, base + s * 0.35),
                       (cx + s * 0.15, base + s * 0.1), (cx + s * 0.02, base + s * 0.1)], fill=NERO)


# ------------------------- DATI -------------------------
def scarica_meteo(citta):
    if os.environ.get("DEMO"):
        oggi = dt.datetime.now(TZ).date()
        return {"temp": 14.3, "code": 2, "giorni": [
            {"data": oggi + dt.timedelta(days=i), "code": c, "max": 16 - i, "min": 8 - i, "pioggia": p,
             "raffiche": 72 if (i == 1 and citta["nome"] == "Rosolini") else 20, "mm": 2,
             "alba": "07:12", "tramonto": "16:51"}
            for i, (c, p) in enumerate([(2, 10), (61, 70), (3, 30), (0, 0)])]}
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": citta["lat"], "longitude": citta["lon"],
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                 "precipitation_sum,wind_gusts_10m_max,sunrise,sunset",
        "timezone": "Europe/Rome", "forecast_days": 4,
    }, timeout=30)
    r.raise_for_status()
    j = r.json()
    dd = j["daily"]
    giorni = [{"data": dt.date.fromisoformat(dd["time"][i]), "code": dd["weather_code"][i],
               "max": dd["temperature_2m_max"][i], "min": dd["temperature_2m_min"][i],
               "pioggia": dd["precipitation_probability_max"][i] or 0,
               "mm": dd["precipitation_sum"][i] or 0, "raffiche": dd["wind_gusts_10m_max"][i] or 0,
               "alba": dd["sunrise"][i][-5:], "tramonto": dd["sunset"][i][-5:]}
              for i in range(len(dd["time"]))]
    return {"temp": j["current"]["temperature_2m"], "code": j["current"]["weather_code"], "giorni": giorni}


def scarica_eventi(da, a):
    """Restituisce {data: [(ordine, ora, titolo), ...]} per i giorni da 'da' (incluso) ad 'a' (escluso)."""
    per_giorno = {}

    def aggiungi(g, ordine, ora, titolo):
        if da <= g < a:
            per_giorno.setdefault(g, []).append((ordine, ora, titolo))

    if os.environ.get("DEMO"):
        oggi = dt.datetime.now(TZ).date()
        prove = [(0, 0, "", "Compleanno di Marco"), (0, 1, "09:30", "Riunione di lavoro con il team"),
                 (0, 1, "18:00", "Palestra"), (1, 1, "12:30", "Pranzo con Giulia"), (3, 1, "10:00", "Dentista"),
                 (6, 1, "20:00", "Cena"), (9, 0, "", "Ferie"), (9, 1, "15:00", "Volo"), (12, 1, "08:00", "Analisi"),
                 (-4, 1, "17:00", "Calcetto"), (-2, 1, "11:00", "Banca"), (14, 1, "09:00", "Corso"),
                 (14, 1, "14:00", "Telefonata"), (14, 1, "16:00", "Spesa"), (14, 1, "19:00", "Pizza")]
        for off, o, ora, t in prove:
            aggiungi(oggi + dt.timedelta(days=off), o, ora, t)
    else:
        import icalendar
        import recurring_ical_events
        indirizzi = os.environ.get("ICS_URL", "").replace(",", " ").split()
        if not indirizzi:
            raise RuntimeError("ICS_URL mancante")
        inizio = dt.datetime.combine(da, dt.time(), TZ)
        fine = dt.datetime.combine(a, dt.time(), TZ)
        tutti = []
        for url in indirizzi:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            cal = icalendar.Calendar.from_ical(r.content)
            tutti.extend(recurring_ical_events.of(cal).between(inizio, fine))
        for e in tutti:
            s = e["DTSTART"].dt
            titolo = str(e.get("SUMMARY", "(senza titolo)")) if MOSTRA_TITOLI else "Impegno"
            if isinstance(s, dt.datetime):
                if s.tzinfo is None:
                    s = s.replace(tzinfo=TZ)
                s = s.astimezone(TZ)
                if s.date() < da:
                    aggiungi(da, 1, "in corso", titolo)
                else:
                    aggiungi(s.date(), 1, s.strftime("%H:%M"), titolo)
            else:
                aggiungi(max(s, da), 0, "", titolo)
    # festività nazionali
    for anno in range(da.year, a.year + 1):
        for g, nome in festivita(anno).items():
            aggiungi(g, -1, "", "★ " + nome)
    for g in per_giorno:
        per_giorno[g].sort()
    return per_giorno


def pasqua(anno):
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese = (h + l - 7 * m + 114) // 31
    giorno = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(anno, mese, giorno)


def festivita(anno):
    p = pasqua(anno)
    f = {
        dt.date(anno, 1, 1): "Capodanno", dt.date(anno, 1, 6): "Epifania",
        p: "Pasqua", p + dt.timedelta(days=1): "Pasquetta",
        dt.date(anno, 4, 25): "Liberazione", dt.date(anno, 5, 1): "Festa del Lavoro",
        dt.date(anno, 6, 2): "Festa della Repubblica", dt.date(anno, 8, 15): "Ferragosto",
        dt.date(anno, 11, 1): "Ognissanti", dt.date(anno, 12, 8): "Immacolata",
        dt.date(anno, 12, 25): "Natale", dt.date(anno, 12, 26): "Santo Stefano",
    }
    if anno >= 2026:  # San Francesco torna festa nazionale dal 2026
        f[dt.date(anno, 10, 4)] = "San Francesco"
    return f


def fase_lunare(giorno):
    """Restituisce (frazione 0-1 del ciclo, nome della fase)."""
    rif = dt.datetime(2000, 1, 6, 18, 14)
    ciclo = 29.530588853
    giorni = (dt.datetime.combine(giorno, dt.time(12)) - rif).total_seconds() / 86400
    f = (giorni % ciclo) / ciclo
    nomi = ["Luna nuova", "Luna crescente", "Primo quarto", "Gibbosa crescente",
            "Luna piena", "Gibbosa calante", "Ultimo quarto", "Luna calante"]
    return f, nomi[int((f * 8) + 0.5) % 8]


def icona_luna(img, cx, cy, r, f):
    import math
    px = img.load()
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            if x * x + y * y > r * r:
                continue
            xn, yn = x / r, y / r
            t = math.sqrt(max(0.0, 1 - yn * yn))
            if f < 0.5:
                illuminato = xn >= math.cos(2 * math.pi * f) * t
            else:
                illuminato = xn <= -math.cos(2 * math.pi * f) * t
            px[cx + x, cy + y] = BIANCO if illuminato else NERO
    ImageDraw.Draw(img).ellipse([cx - r, cy - r, cx + r, cy + r], outline=NERO, width=2)


# ------------------------- BLOCCHI COMUNI -------------------------
def intestazione(img, d, oggi, meteo):
    d.text((40, 30), f"{GIORNI[oggi.weekday()]} {oggi.day} {MESI[oggi.month - 1]}", font=font(70, True), fill=NERO)
    x = 40
    riga = f"{oggi.year}"
    m = meteo[0] if meteo else None
    if m:
        riga += f"    Alba {m['giorni'][0]['alba']}  ·  Tramonto {m['giorni'][0]['tramonto']}"
    d.text((x, 118), riga, font=font(28), fill=GRIGIO)
    x += d.textlength(riga, font=font(28)) + 36
    f, nome = fase_lunare(oggi)
    icona_luna(img, int(x + 15), 136, 15, f)
    d.text((x + 42, 118), nome, font=font(28), fill=GRIGIO)
    d.line([(40, 170), (W - 40, 170)], fill=NERO, width=3)


def piede(d, ora, vista):
    d.text((40, H - 30), f"Vista: {vista}", font=font(22), fill=GRIGIO, anchor="lm")
    d.text((W - 40, H - 30), f"Aggiornato alle {ora.strftime('%H:%M')}", font=font(22), fill=GRIGIO, anchor="rm")


def meteo_completo(d, meteo, y0):
    """Meteo grande con previsioni dei prossimi 3 giorni. Restituisce la y finale."""
    meta = W // 2
    for i, (citta, m) in enumerate(zip(CITTA[:2], meteo)):
        x0, pad = i * meta, 36
        d.text((x0 + pad, y0), citta["nome"], font=font(40, True), fill=NERO)
        if m is None:
            d.text((x0 + pad, y0 + 80), "Meteo non disponibile", font=font(28), fill=GRIGIO)
            continue
        icona(d, x0 + pad + 70, y0 + 150, 130, m["code"])
        d.text((x0 + pad + 170, y0 + 95), f"{round(m['temp'])}°", font=font(96, True), fill=NERO)
        g0 = m["giorni"][0]
        d.text((x0 + pad, y0 + 240), tronca(d, METEO_TESTO.get(m["code"], ""), font(28), meta - 2 * pad),
               font=font(28), fill=NERO)
        d.text((x0 + pad, y0 + 282), f"Min {round(g0['min'])}°   Max {round(g0['max'])}°   Pioggia {g0['pioggia']}%",
               font=font(24), fill=GRIGIO)
        col = (meta - 2 * pad) / 3
        for j, g in enumerate(m["giorni"][1:4]):
            cx = x0 + pad + col * j + col / 2
            d.text((cx, y0 + 345), GIORNI_BREVI[g["data"].weekday()], font=font(28, True), fill=NERO, anchor="mm")
            icona(d, cx, y0 + 410, 64, g["code"])
            d.text((cx, y0 + 470), f"{round(g['max'])}° / {round(g['min'])}°", font=font(24), fill=NERO, anchor="mm")
    d.line([(meta, y0 + 10), (meta, y0 + 490)], fill=GRIGIO_CHIARO, width=2)
    d.line([(40, y0 + 520), (W - 40, y0 + 520)], fill=NERO, width=3)
    return y0 + 545


def meteo_compatto(d, meteo, y0):
    """Meteo su una riga per città, senza previsioni. Restituisce la y finale."""
    meta = W // 2
    for i, (citta, m) in enumerate(zip(CITTA[:2], meteo)):
        x0, pad = i * meta, 36
        d.text((x0 + pad, y0), citta["nome"], font=font(34, True), fill=NERO)
        if m is None:
            d.text((x0 + pad, y0 + 60), "Meteo non disponibile", font=font(26), fill=GRIGIO)
            continue
        icona(d, x0 + pad + 50, y0 + 105, 90, m["code"])
        d.text((x0 + pad + 120, y0 + 60), f"{round(m['temp'])}°", font=font(72, True), fill=NERO)
        g0 = m["giorni"][0]
        x_info = x0 + pad + 280
        d.text((x_info, y0 + 72), f"Min {round(g0['min'])}°  Max {round(g0['max'])}°", font=font(22), fill=GRIGIO)
        d.text((x_info, y0 + 104), f"Pioggia {g0['pioggia']}%", font=font(22), fill=GRIGIO)
        d.text((x0 + pad, y0 + 152), tronca(d, METEO_TESTO.get(m["code"], ""), font(24), meta - 2 * pad),
               font=font(24), fill=NERO)
    d.line([(meta, y0 + 5), (meta, y0 + 175)], fill=GRIGIO_CHIARO, width=2)
    d.line([(40, y0 + 195), (W - 40, y0 + 195)], fill=NERO, width=3)
    return y0 + 218


def etichetta(g, oggi, breve=False):
    if g == oggi:
        return "Oggi"
    if g == oggi + dt.timedelta(days=1):
        return "Domani"
    if breve:
        return f"{GIORNI_BREVI[g.weekday()]} {g.day}"
    return f"{GIORNI[g.weekday()]} {g.day} {MESI[g.month - 1]}"


# ------------------------- LE TRE VISTE -------------------------
def vista_giorno(d, oggi, meteo, eventi):
    y = meteo_completo(d, meteo, 195)
    limite = LIMITE
    for g, titolo_sezione, grande in ((oggi, "Oggi", True), (oggi + dt.timedelta(days=1), "Domani", False)):
        if y + 120 > limite:
            break
        d.text((40, y), titolo_sezione, font=font(44 if grande else 34, True), fill=NERO if grande else GRIGIO)
        y += 70 if grande else 56
        lista = eventi.get(g, [])
        if not lista:
            d.text((60, y), "Nessun impegno", font=font(30 if grande else 26), fill=GRIGIO)
            y += 60
            continue
        f_ora = font(32 if grande else 26, True)
        f_tit = font(34 if grande else 26)
        passo = 52 if grande else 40
        for idx, (_, ora, titolo) in enumerate(lista):
            if y + passo > limite:
                d.text((60, y), f"+ altri {len(lista) - idx}", font=font(24), fill=GRIGIO)
                y += passo
                break
            colore = NERO if grande else GRIGIO
            d.text((60, y), ora if ora else ("Festa" if titolo.startswith("★") else "Tutto il giorno"), font=f_ora if ora else font(22), fill=colore)
            d.text((300, y), tronca(d, titolo, f_tit, W - 340), font=f_tit, fill=colore)
            y += passo
        y += 20


def vista_settimana(d, oggi, meteo, eventi):
    y = meteo_compatto(d, meteo, 190)
    d.text((40, y), "Prossimi 7 giorni", font=font(40, True), fill=NERO)
    y += 66
    limite = LIMITE
    giorni = [oggi + dt.timedelta(days=i) for i in range(7)]
    # spazio garantito: almeno una riga per ogni giorno
    riga = 42
    extra_disponibili = (limite - y - 7 * (riga + 22)) // riga
    for g in giorni:
        lista = eventi.get(g, [])
        y_inizio = y
        if g == oggi:
            d.rectangle([36, y - 4, 36 + d.textlength("Oggi", font=font(30, True)) + 20, y + 38], fill=NERO)
            d.text((46, y), "Oggi", font=font(30, True), fill=BIANCO)
        else:
            d.text((46, y), etichetta(g, oggi, breve=True), font=font(30, True), fill=NERO)
        if not lista:
            d.text((260, y + 2), "—", font=font(28), fill=GRIGIO_CHIARO)
            y += riga
        else:
            mostrabili = 1 + max(0, min(len(lista) - 1, extra_disponibili))
            for idx, (_, ora, titolo) in enumerate(lista[:mostrabili]):
                if idx == mostrabili - 1 and mostrabili < len(lista):
                    titolo = f"{titolo}  (+{len(lista) - mostrabili})"
                d.text((260, y + 2), ora if ora else ("Festa" if titolo.startswith("★") else "Giorno"), font=font(26, True) if ora else font(22), fill=NERO if ora else GRIGIO)
                d.text((380, y), tronca(d, titolo, font(28), W - 420), font=font(28), fill=NERO)
                y += riga
            extra_disponibili -= mostrabili - 1
        y = max(y, y_inizio + riga) + 10
        d.line([(40, y), (W - 40, y)], fill=GRIGIO_CHIARO, width=1)
        y += 12


def vista_mese(d, oggi, meteo, eventi):
    y = meteo_compatto(d, meteo, 190)
    d.text((40, y), f"{MESI[oggi.month - 1].capitalize()} {oggi.year}", font=font(40, True), fill=NERO)
    y += 64
    x0, larghezza = 40, W - 80
    cw = larghezza / 7
    for i, nome in enumerate(GIORNI_BREVI):
        d.text((x0 + cw * i + cw / 2, y + 16), nome, font=font(24, True),
               fill=GRIGIO if i >= 5 else NERO, anchor="mm")
    y += 40
    settimane = calendar.Calendar(firstweekday=0).monthdatescalendar(oggi.year, oggi.month)
    ch = (LIMITE - y) / len(settimane)
    f_ev = font(19)
    for r, settimana in enumerate(settimane):
        for c, g in enumerate(settimana):
            cx, cy = x0 + cw * c, y + ch * r
            d.rectangle([cx, cy, cx + cw, cy + ch], outline=GRIGIO_CHIARO, width=1)
            fuori = g.month != oggi.month
            num = str(g.day)
            if g == oggi:
                d.rectangle([cx + 4, cy + 4, cx + 48, cy + 40], fill=NERO)
                d.text((cx + 26, cy + 22), num, font=font(24, True), fill=BIANCO, anchor="mm")
            else:
                d.text((cx + 26, cy + 22), num, font=font(24, True),
                       fill=GRIGIO_CHIARO if fuori else (GRIGIO if c >= 5 else NERO), anchor="mm")
            if fuori:
                continue
            lista = eventi.get(g, [])
            righe = int((ch - 48) // 24)
            for idx, (_, ora, titolo) in enumerate(lista[:righe]):
                if idx == righe - 1 and len(lista) > righe:
                    testo = f"+{len(lista) - righe + 1} altri"
                else:
                    testo = titolo
                d.text((cx + 6, cy + 46 + idx * 24), tronca(d, testo, f_ev, cw - 10), font=f_ev, fill=NERO)


def avvisi_meteo(meteo):
    avvisi = []
    for citta, m in zip(CITTA[:2], meteo):
        if not m:
            continue
        for g in m["giorni"][:2]:
            quando = "oggi" if g is m["giorni"][0] else "domani"
            motivi = []
            if g["code"] in (95, 96, 99):
                motivi.append("temporali")
            if g["raffiche"] >= SOGLIA_RAFFICHE_KMH:
                motivi.append(f"raffiche fino a {round(g['raffiche'])} km/h")
            if g["mm"] >= SOGLIA_PIOGGIA_MM:
                motivi.append(f"pioggia abbondante ({round(g['mm'])} mm)")
            if g["max"] >= SOGLIA_CALDO:
                motivi.append(f"caldo intenso ({round(g['max'])}°)")
            if g["min"] <= SOGLIA_GELO:
                motivi.append(f"gelo ({round(g['min'])}°)")
            if motivi:
                avvisi.append(f"{citta['nome']} {quando}: " + ", ".join(motivi))
    return avvisi


def barra_info(d, oggi, meteo, eventi):
    y = LIMITE + 12
    d.line([(40, y), (W - 40, y)], fill=NERO, width=2)
    y += 14
    righe = []
    feste_oggi = [t[2:] for _, _, t in eventi.get(oggi, []) if t.startswith("★ ")]
    if feste_oggi:
        righe.append("Oggi è festa: " + ", ".join(feste_oggi))
    domani = oggi + dt.timedelta(days=1)
    if RACCOLTA.get(domani.weekday()):
        righe.append(f"Raccolta di domani: {RACCOLTA[domani.weekday()]}")
    for a in avvisi_meteo(meteo):
        righe.append("Attenzione · " + a)
    for testo in righe[:2]:
        d.text((40, y), tronca(d, testo, font(24, True), W - 80), font=font(24, True), fill=NERO)
        y += 34
    frase = FRASI[oggi.toordinal() % len(FRASI)] if FRASI else ""
    if frase:
        d.text((W / 2, H - 66), tronca(d, f"«{frase}»", font(26, corsivo=True), W - 80),
               font=font(26, corsivo=True), fill=GRIGIO, anchor="mm")


VISTE = {"giorno": vista_giorno, "settimana": vista_settimana, "mese": vista_mese}


def main():
    ora = dt.datetime.now(TZ)
    oggi = ora.date()

    meteo = []
    for c in CITTA[:2]:
        try:
            meteo.append(scarica_meteo(c))
        except Exception as ex:
            print("Errore meteo", c["nome"], ex)
            meteo.append(None)

    primo_mese = oggi.replace(day=1)
    fine_mese = primo_mese + dt.timedelta(days=calendar.monthrange(oggi.year, oggi.month)[1])
    try:
        eventi = scarica_eventi(min(primo_mese, oggi), max(fine_mese, oggi + dt.timedelta(days=8)))
        errore_cal = False
    except Exception as ex:
        print("Errore calendario:", ex)
        eventi, errore_cal = {}, True

    scelta = (os.environ.get("VISTA") or VISTA_PREDEFINITA).strip().lower()
    if scelta == "auto":
        scelta = VISTE_AUTOMATICHE[-1][1]
        for ora_inizio, nome in sorted(VISTE_AUTOMATICHE):
            if ora.hour >= ora_inizio:
                scelta = nome
    if scelta not in VISTE:
        scelta = VISTA_PREDEFINITA

    for nome, funzione in VISTE.items():
        img = Image.new("L", (W, H), BIANCO)
        d = ImageDraw.Draw(img)
        intestazione(img, d, oggi, meteo)
        funzione(d, oggi, meteo, eventi)
        barra_info(d, oggi, meteo, eventi)
        if errore_cal:
            d.text((W / 2, LIMITE - 10), "Calendario non disponibile", font=font(24, True), fill=NERO, anchor="mm")
        piede(d, ora, nome)
        img.save(f"dash-{nome}.png")
        if nome == scelta:
            img.save("dash.png")
    print("Immagini create. Vista scelta:", scelta)


if __name__ == "__main__":
    main()
