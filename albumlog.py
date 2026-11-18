#!/usr/bin/env python3
"""Minimal offline album log and wishlist manager: tiny, personal, anti-RateYourMusic."""

import argparse
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date, datetime

FOLDER = os.path.expanduser("~/.local/share/albumlog")
DATA = os.path.join(FOLDER, "log.tsv")
WISHLIST = os.path.join(FOLDER, "wishlist.tsv")
FIELDS = ["date", "artist", "album", "year", "listen", "favorite",
          "format", "genre", "country", "note"]
OLD_FIELDS = ["date", "artist", "album", "year", "listen", "favorite", "note"]
WISH_FIELDS = ["added", "artist", "album", "priority", "note"]
HEART = "♥"   # favorite in the log
STAR = "★"    # priority on the wishlist
DEFAULT_FORMAT = "digital"
FORMATS = ["digital", "vinyl", "CD", "cassette"]
FORMAT_ALIASES = {
    "d": "digital", "digital": "digital",
    "v": "vinyl", "vinyl": "vinyl", "lp": "vinyl",
    "cd": "CD",
    "k": "cassette", "ca": "cassette", "cas": "cassette",
    "cassette": "cassette", "tape": "cassette",
}
COMMANDS = {"add", "list", "fav", "edit", "rm", "artists", "years", "tags",
            "stats", "wish"}
WISH_COMMANDS = {"add", "list", "edit", "rm", "done", "pick", "star"}

# Sort keys for the list view. Descending for the ones in DESC.
SORTS = {
    "date": lambda r: (r["date"], r["id"]),
    "artist": lambda r: (r["artist"].lower(), r["album"].lower(), r["year"]),
    "album": lambda r: (r["album"].lower(), r["artist"].lower()),
    "year": lambda r: (int(r["year"]) if r["year"].isdigit() else 0,
                       r["artist"].lower()),
    "fav": lambda r: (r["favorite"] == "yes", r["date"], r["id"]),
}
DESC = {"date", "fav"}

WISH_SORTS = {
    "added": lambda r: (r["added"], r["id"]),
    "priority": lambda r: (r["priority"] != "yes", r["added"], r["id"]),
    "artist": lambda r: (r["artist"].lower(), r["album"].lower()),
    "album": lambda r: (r["album"].lower(), r["artist"].lower()),
}

# ISO 3166-1 alpha-2 codes. Only the code is saved in the log.
_COUNTRY_DATA = """\
AD Andorra
AE United Arab Emirates
AF Afghanistan
AG Antigua and Barbuda
AI Anguilla
AL Albania
AM Armenia
AO Angola
AQ Antarctica
AR Argentina
AS American Samoa
AT Austria
AU Australia
AW Aruba
AX Åland Islands
AZ Azerbaijan
BA Bosnia and Herzegovina
BB Barbados
BD Bangladesh
BE Belgium
BF Burkina Faso
BG Bulgaria
BH Bahrain
BI Burundi
BJ Benin
BL Saint Barthélemy
BM Bermuda
BN Brunei
BO Bolivia
BQ Bonaire, Sint Eustatius and Saba
BR Brazil
BS Bahamas
BT Bhutan
BV Bouvet Island
BW Botswana
BY Belarus
BZ Belize
CA Canada
CC Cocos (Keeling) Islands
CD Democratic Republic of the Congo
CF Central African Republic
CG Republic of the Congo
CH Switzerland
CI Côte d'Ivoire
CK Cook Islands
CL Chile
CM Cameroon
CN China
CO Colombia
CR Costa Rica
CU Cuba
CV Cabo Verde
CW Curaçao
CX Christmas Island
CY Cyprus
CZ Czechia
DE Germany
DJ Djibouti
DK Denmark
DM Dominica
DO Dominican Republic
DZ Algeria
EC Ecuador
EE Estonia
EG Egypt
EH Western Sahara
ER Eritrea
ES Spain
ET Ethiopia
FI Finland
FJ Fiji
FK Falkland Islands
FM Micronesia
FO Faroe Islands
FR France
GA Gabon
GB United Kingdom
GD Grenada
GE Georgia
GF French Guiana
GG Guernsey
GH Ghana
GI Gibraltar
GL Greenland
GM Gambia
GN Guinea
GP Guadeloupe
GQ Equatorial Guinea
GR Greece
GS South Georgia and the South Sandwich Islands
GT Guatemala
GU Guam
GW Guinea-Bissau
GY Guyana
HK Hong Kong
HM Heard Island and McDonald Islands
HN Honduras
HR Croatia
HT Haiti
HU Hungary
ID Indonesia
IE Ireland
IL Israel
IM Isle of Man
IN India
IO British Indian Ocean Territory
IQ Iraq
IR Iran
IS Iceland
IT Italy
JE Jersey
JM Jamaica
JO Jordan
JP Japan
KE Kenya
KG Kyrgyzstan
KH Cambodia
KI Kiribati
KM Comoros
KN Saint Kitts and Nevis
KP North Korea
KR South Korea
KW Kuwait
KY Cayman Islands
KZ Kazakhstan
LA Laos
LB Lebanon
LC Saint Lucia
LI Liechtenstein
LK Sri Lanka
LR Liberia
LS Lesotho
LT Lithuania
LU Luxembourg
LV Latvia
LY Libya
MA Morocco
MC Monaco
MD Moldova
ME Montenegro
MF Saint Martin
MG Madagascar
MH Marshall Islands
MK North Macedonia
ML Mali
MM Myanmar
MN Mongolia
MO Macao
MP Northern Mariana Islands
MQ Martinique
MR Mauritania
MS Montserrat
MT Malta
MU Mauritius
MV Maldives
MW Malawi
MX Mexico
MY Malaysia
MZ Mozambique
NA Namibia
NC New Caledonia
NE Niger
NF Norfolk Island
NG Nigeria
NI Nicaragua
NL Netherlands
NO Norway
NP Nepal
NR Nauru
NU Niue
NZ New Zealand
OM Oman
PA Panama
PE Peru
PF French Polynesia
PG Papua New Guinea
PH Philippines
PK Pakistan
PL Poland
PM Saint Pierre and Miquelon
PN Pitcairn Islands
PR Puerto Rico
PS Palestine
PT Portugal
PW Palau
PY Paraguay
QA Qatar
RE Réunion
RO Romania
RS Serbia
RU Russia
RW Rwanda
SA Saudi Arabia
SB Solomon Islands
SC Seychelles
SD Sudan
SE Sweden
SG Singapore
SH Saint Helena, Ascension and Tristan da Cunha
SI Slovenia
SJ Svalbard and Jan Mayen
SK Slovakia
SL Sierra Leone
SM San Marino
SN Senegal
SO Somalia
SR Suriname
SS South Sudan
ST São Tomé and Príncipe
SV El Salvador
SX Sint Maarten
SY Syria
SZ Eswatini
TC Turks and Caicos Islands
TD Chad
TF French Southern Territories
TG Togo
TH Thailand
TJ Tajikistan
TK Tokelau
TL Timor-Leste
TM Turkmenistan
TN Tunisia
TO Tonga
TR Türkiye
TT Trinidad and Tobago
TV Tuvalu
TW Taiwan
TZ Tanzania
UA Ukraine
UG Uganda
UM United States Minor Outlying Islands
US United States
UY Uruguay
UZ Uzbekistan
VA Vatican City
VC Saint Vincent and the Grenadines
VE Venezuela
VG British Virgin Islands
VI U.S. Virgin Islands
VN Vietnam
VU Vanuatu
WF Wallis and Futuna
WS Samoa
YE Yemen
YT Mayotte
ZA South Africa
ZM Zambia
ZW Zimbabwe
"""
COUNTRIES = dict(line.split(" ", 1) for line in _COUNTRY_DATA.splitlines())
NAME_INDEX = {name.casefold(): code for code, name in COUNTRIES.items()}
ALIASES = {
    "uk": "GB", "great britain": "GB", "england": "GB", "scotland": "GB",
    "wales": "GB", "northern ireland": "GB",
    "usa": "US", "united states of america": "US",
    "czech republic": "CZ", "turkey": "TR", "ivory coast": "CI",
}

HELP_EPILOG = """\
storage:
  ~/.local/share/albumlog/log.tsv        albums you listened to
  ~/.local/share/albumlog/wishlist.tsv   albums you plan to listen to
  Plain tab-separated text with a header row. Both open in LibreOffice
  or Excel (choose Tab as the separator and UTF-8 as the encoding), and
  you can edit them by hand. To make an XLSX, open a file and save it as
  XLSX. Back up by copying the albumlog folder.

commands:
  add               add an entry to the log (asks for each field)
  list              show log entries in boxed tables (default command)
  artists           summary per artist
  years             summary per release year (or listening year)
  tags [genre|country|format]
                    summary per genre, country or format
  stats             totals for the log and the wishlist (also: --stats)
  fav ID            toggle the favorite heart on an entry
  edit ID           edit an entry (Enter keeps a value, "-" clears optional ones)
  rm ID             remove an entry
  wish ...          the wishlist (see below)

symbols:
  ♥  favorite in the log
  ★  priority on the wishlist

format:
  Asked right before genre and country. It defaults to digital (press
  Enter). Accepted values:
     digital   d
     vinyl     v  (or lp)
     CD        cd
     cassette  k  (or ca, tape)
  Entries without a format (for example from an older file) count as
  digital. Filter with -F, for example: albumlog -F vinyl

countries:
  Countries are optional. At the prompt, press y to open an fzf menu with
  all countries, type to search by name or code, press Tab to mark several
  and Enter to confirm (Esc cancels). Only the ISO 3166-1 alpha-2 code is
  saved, for example JP or US. Other ways to answer the prompt:
     jp, brazil     type codes or names directly
     -              clear the current value
     Enter          skip, or keep the current value

  Without fzf installed, you are asked to type codes or names instead.
  Filters accept a code or a name: albumlog -c jp  or  albumlog -c japan
  Note: England, Scotland and Wales have no code of their own and are
  saved as GB.

wishlist:
  wish add          add an album (artist, album, priority, optional note)
  wish list         show the wishlist (default wish command)
  wish edit ID      edit a wishlist entry
  wish star ID      toggle the priority star on an entry
  wish rm ID        remove a wishlist entry
  wish done ID      you listened to it: opens the normal "add" questions
                    with artist, album and note prefilled, saves it in the
                    log, and removes it from the wishlist
  wish pick         pick a random album from the wishlist

  The date each album was added is saved automatically. List options:
     -s added|priority|artist|album   sort order (default: added)
     -p                               priority albums only
     -r                               reverse the order
     -g TEXT                          search artist, album and note
  Pick option:
     -p                               pick only among priority albums

  Adding an album that is already on the wishlist is refused. If it is
  already in your log, you are warned and asked to confirm.

stats:
  albumlog stats shows two boxes. Log: entries, distinct albums, artists,
  favorite albums, first and last listens, albums per format, earliest
  and latest dates, top genre and top country. Wishlist: albums waiting,
  priority albums, the oldest one waiting, and how many are already in
  your log.

tags:
  Genres accept several values separated by commas, for example:
  indie rock, noise pop
  If an album is already in the log, the next entry for it is saved as a
  "last" listen without asking, and year, format, genre and country are
  prefilled from the earlier entry.

list navigation:
  n / Enter  next page        p  previous page
  d  sort by date             f  favorites first
  a  sort by artist           b  sort by album
  y  sort by year             r  reverse the current order
  q  quit

examples:
  albumlog add                     add a new entry
  albumlog                         browse everything, newest first
  albumlog -f                      favorites only
  albumlog -F vinyl                only entries heard on vinyl
  albumlog -t "indie rock"         only entries with that genre
  albumlog -c japan -s year        only that country, sorted by year
  albumlog -g dinosaur             search artist, album, year, tags, note
  albumlog -l first                only first listens
  albumlog artists -s albums       artists with the most albums first
  albumlog years --listened        albums logged per listening year
  albumlog tags format             albums per format
  albumlog tags country            albums per country
  albumlog stats                   totals for the log and the wishlist
  albumlog fav 12                  toggle the heart on entry 12
  albumlog wish add                add an album to the wishlist
  albumlog wish -p                 priority albums on the wishlist
  albumlog wish star 3             toggle priority on wishlist entry 3
  albumlog wish pick -p            pick among priority albums
  albumlog wish done 3             move wishlist entry 3 into the log
"""


# ---------- display helpers (same approach as lastfm) ----------

def cw(text):
    """Display width of a string (handles accents and wide characters)."""
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def fit(text, width, right=False):
    if cw(text) > width:
        out, used = "", 0
        for ch in text:
            w = cw(ch)
            if used + w > width - 3:
                break
            out += ch
            used += w
        text = out + "..."
    pad = " " * (width - cw(text))
    return pad + text if right else text + pad


def table(rows, header, right=(), measure=None):
    """Boxed table with a header. `measure` sizes columns from a larger set."""
    ncols = len(header)
    basis = [header] + (measure if measure is not None else rows)
    widths = [max(cw(r[i]) for r in basis) for i in range(ncols)]
    total = shutil.get_terminal_size((80, 24)).columns
    excess = sum(widths) + 3 * ncols + 1 - total

    while excess > 0:
        i = max(range(ncols), key=lambda k: widths[k])
        if widths[i] <= 8:
            break
        widths[i] -= 1
        excess -= 1

    def rule(left, mid, rgt):
        return left + mid.join("─" * (w + 2) for w in widths) + rgt

    def line(r):
        cells = [fit(r[i], widths[i], right=i in right) for i in range(ncols)]
        return "│ " + " │ ".join(cells) + " │"

    print(rule("┌", "┬", "┐"))
    print(line(header))
    print(rule("├", "┼", "┤"))
    for r in rows:
        print(line(r))
    print(rule("└", "┴", "┘"))


def cells(r):
    return (str(r["id"]), r["date"], r["artist"], r["album"], r["year"],
            r["listen"], HEART if r["favorite"] == "yes" else "",
            r["format"], r["genre"], r["country"], r["note"])


HEADER = ("#", "Date", "Artist", "Album", "Year", "Listen", HEART,
          "Format", "Genre", "Country", "Note")
RIGHT = (0, 4)

WISH_HEADER = ("#", "Added", "Artist", "Album", STAR, "Note")
WISH_RIGHT = (0,)


def wish_cells(r):
    return (str(r["id"]), r["added"], r["artist"], r["album"],
            STAR if r["priority"] == "yes" else "", r["note"])


# ---------- formats, tags and countries ----------

def normalize_format(text):
    """Return the canonical format name, or None if it is not recognized."""
    return FORMAT_ALIASES.get(text.strip().casefold())


def format_arg(text):
    fmt = normalize_format(text)
    if not fmt:
        raise argparse.ArgumentTypeError(
            f"invalid format '{text}' (use digital, vinyl, CD or cassette)")
    return fmt


def tags_of(text):
    return [t.strip() for t in text.split(",") if t.strip()]


def parse_tags(text, lower=False):
    """Normalize a comma-separated tag string: trimmed, no duplicates."""
    seen, out = set(), []
    for t in tags_of(text.replace(";", ",")):
        t = t.lower() if lower else t
        if t.casefold() not in seen:
            seen.add(t.casefold())
            out.append(t)
    return ", ".join(out)


def has_tag(text, wanted):
    return wanted.casefold() in (t.casefold() for t in tags_of(text))


def resolve_country(text):
    """Return the alpha-2 code for a code or a country name, else None."""
    t = text.strip()
    if len(t) == 2 and t.upper() in COUNTRIES:
        return t.upper()
    k = t.casefold()
    if k in ALIASES:
        return ALIASES[k]
    if k in NAME_INDEX:
        return NAME_INDEX[k]
    if len(k) >= 3:
        hits = [c for n, c in NAME_INDEX.items() if n.startswith(k)]
        if len(hits) == 1:
            return hits[0]
    return None


def resolve_list(text):
    """Split a comma-separated string into (codes, unknown tokens)."""
    codes, bad = [], []
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        code = resolve_country(token)
        if not code:
            bad.append(token)
        elif code not in codes:
            codes.append(code)
    return codes, bad


def country_label(code):
    return f"{code} {COUNTRIES[code]}" if code in COUNTRIES else code


def country_names(text):
    return ", ".join(country_label(c.upper()) for c in tags_of(text))


def pick_countries():
    """Choose countries with fzf, or by typing. Returns codes or None."""
    if shutil.which("fzf"):
        items = sorted(COUNTRIES.items(), key=lambda x: x[1].casefold())
        lines = "\n".join(f"{c}  {n}" for c, n in items)
        try:
            res = subprocess.run(
                ["fzf", "--multi", "--height", "40%", "--reverse",
                 "--prompt", "Country> ",
                 "--header", "Tab: mark several | Enter: confirm | Esc: cancel"],
                input=lines, stdout=subprocess.PIPE, text=True)
        except OSError:
            return None
        if res.returncode != 0:
            return None
        return [ln.split()[0] for ln in res.stdout.splitlines() if ln.strip()]
    print("fzf not found; type country codes or names instead")
    while True:
        ans = clean(input("Countries, comma-separated (Enter to cancel): "))
        if not ans:
            return None
        codes, bad = resolve_list(ans)
        if not bad:
            return codes
        print("unknown: " + ", ".join(bad))


def prompt_countries(current):
    shown = f" [{current}]" if current else ""
    hint = "y = choose, - = clear, Enter = keep" if current \
        else "y = choose, Enter = skip"
    while True:
        ans = clean(input(f"Countries{shown} ({hint}): "))
        if not ans:
            return current
        if ans == "-":
            return ""
        if ans.lower() in ("y", "yes"):
            codes = pick_countries()
            if codes is None:
                return current
        else:
            codes, bad = resolve_list(ans)
            if bad:
                print("unknown: " + ", ".join(bad))
                continue
        print("selected: " + (", ".join(country_label(c) for c in codes)
                              or "none"))
        return ", ".join(codes)


# ---------- storage ----------

def clean(text):
    """Collapse tabs and newlines so one entry always stays on one line."""
    return " ".join(text.split())


def read_tsv(path, fields, default_columns):
    """Read a tab-separated file into dicts with a position-based id."""
    rows = []
    if not os.path.isfile(path):
        return rows
    columns = default_columns  # files without a header use this layout
    first = fields[0] + "\t"
    with open(path, encoding="utf-8", newline="") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith(first):
                columns = line.split("\t")
                continue
            r = {k: "" for k in fields}
            r.update(zip(columns, line.split("\t")))
            rows.append(r)
    for i, r in enumerate(rows, 1):
        r["id"] = i
    return rows


def write_tsv(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")
        for r in rows:
            f.write("\t".join(clean(r[k]) for k in fields) + "\n")
    os.replace(tmp, path)


def load():
    rows = read_tsv(DATA, FIELDS, OLD_FIELDS)
    for r in rows:
        # Missing format counts as digital; common spellings are corrected.
        r["format"] = (normalize_format(r["format"]) or r["format"]
                       if r["format"] else DEFAULT_FORMAT)
    return rows


def save(rows):
    write_tsv(DATA, FIELDS, rows)


def wload():
    return read_tsv(WISHLIST, WISH_FIELDS, WISH_FIELDS)


def wsave(rows):
    write_tsv(WISHLIST, WISH_FIELDS, rows)


def find(rows, entry_id):
    for r in rows:
        if r["id"] == entry_id:
            return r
    sys.exit(f"no entry with id {entry_id}")


# ---------- input ----------

def ask(label, default="", check=None):
    while True:
        shown = f" [{default}]" if default else ""
        val = clean(input(f"{label}{shown}: ")) or default
        err = check(val) if check else None
        if not err:
            return val
        print(err)


def optional(label, default=""):
    """Optional field: Enter keeps the current value, "-" clears it."""
    val = ask(label, default)
    return "" if val == "-" else val


def need(val):
    return None if val else "required"


def yes_no(val):
    return None if val.lower() in ("y", "n") else "type y or n"


def check_year(val):
    limit = date.today().year + 1
    if val.isdigit() and 1000 <= int(val) <= limit:
        return None
    return f"enter a year between 1000 and {limit}"


def check_date(val):
    try:
        datetime.strptime(val, "%Y-%m-%d")
    except ValueError:
        return "use YYYY-MM-DD"
    return None


def check_format(val):
    if normalize_format(val):
        return None
    return "type digital (d), vinyl (v), CD (cd) or cassette (k)"


def album_key(r):
    return (r["artist"].casefold(), r["album"].casefold())


def prompt_entry(cur, rows):
    r = dict(cur)
    r["artist"] = ask("Artist", cur["artist"], need)
    r["album"] = ask("Album", cur["album"], need)

    others = [x for x in rows
              if x["id"] != cur["id"] and album_key(x) == album_key(r)]
    base = (others[0] if others else
            {"year": "", "format": DEFAULT_FORMAT, "genre": "", "country": ""})
    if others:
        print(f"already logged {len(others)} time(s); "
              "year, format and tags are prefilled")

    r["year"] = ask("Year", cur["year"] or base["year"], check_year)

    if others:
        r["listen"] = cur["listen"] or "last"
        if not cur["listen"]:
            print("saved as a last listen")
    else:
        listen = ask("Listen: [f]irst or [l]ast", cur["listen"][:1],
                     lambda v: None if v.lower() in ("f", "l", "first", "last")
                     else "type f or l")
        r["listen"] = "first" if listen.lower().startswith("f") else "last"

    fav = ask("Favorite? [y/n]", "y" if cur["favorite"] == "yes" else "n",
              yes_no)
    r["favorite"] = "yes" if fav.lower() == "y" else "no"

    fmt = ask("Format: [d]igital, [v]inyl, [cd], [k] cassette",
              cur["format"] or base["format"] or DEFAULT_FORMAT, check_format)
    r["format"] = normalize_format(fmt)

    r["genre"] = parse_tags(
        optional("Genres, comma-separated (optional)",
                 cur["genre"] or base["genre"]), lower=True)
    r["country"] = prompt_countries(cur["country"] or base["country"])
    r["note"] = optional("Note (optional)", cur["note"])
    r["date"] = ask("Date YYYY-MM-DD", cur["date"], check_date)
    return r


def blank_entry(artist="", album="", note=""):
    return {"id": 0, "date": date.today().isoformat(), "artist": artist,
            "album": album, "year": "", "listen": "", "favorite": "no",
            "format": "", "genre": "", "country": "", "note": note}


# ---------- entry commands ----------

def cmd_add(args):
    rows = load()
    entry = prompt_entry(blank_entry(), rows)
    entry["id"] = len(rows) + 1
    rows.append(entry)
    save(rows)
    print(f"added #{entry['id']}: {entry['artist']} - {entry['album']}")


def cmd_edit(args):
    rows = load()
    r = find(rows, args.id)
    r.update(prompt_entry(r, rows))
    save(rows)
    print(f"updated #{r['id']}")


def cmd_fav(args):
    rows = load()
    r = find(rows, args.id)
    r["favorite"] = "no" if r["favorite"] == "yes" else "yes"
    save(rows)
    state = "marked as favorite" if r["favorite"] == "yes" else "unmarked"
    print(f"#{r['id']} {r['artist']} - {r['album']} {state}")


def cmd_rm(args):
    rows = load()
    r = find(rows, args.id)
    if input(f"Remove #{r['id']} {r['artist']} - {r['album']}? [y/N] ").lower() != "y":
        sys.exit("cancelled")
    rows.remove(r)
    save(rows)
    print("removed (ids after this one have shifted down by one)")


# ---------- wishlist commands ----------

def cmd_wish_add(args):
    wishes = wload()
    logged = load()
    artist = ask("Artist", "", need)
    album = ask("Album", "", need)
    probe = {"artist": artist, "album": album}

    if any(album_key(w) == album_key(probe) for w in wishes):
        sys.exit("already on the wishlist")
    seen = [r for r in logged if album_key(r) == album_key(probe)]
    if seen:
        print(f"already in your log (last on {max(r['date'] for r in seen)})")
        if input("Add to the wishlist anyway? [y/N] ").lower() != "y":
            sys.exit("cancelled")

    prio = ask("Priority? [y/n]", "n", yes_no)
    note = optional("Note (optional)")
    entry = {"id": len(wishes) + 1, "added": date.today().isoformat(),
             "artist": artist, "album": album,
             "priority": "yes" if prio.lower() == "y" else "no", "note": note}
    wishes.append(entry)
    wsave(wishes)
    print(f"added to wishlist #{entry['id']}: {artist} - {album}")


def cmd_wish_edit(args):
    wishes = wload()
    r = find(wishes, args.id)
    r["artist"] = ask("Artist", r["artist"], need)
    r["album"] = ask("Album", r["album"], need)
    prio = ask("Priority? [y/n]", "y" if r["priority"] == "yes" else "n",
               yes_no)
    r["priority"] = "yes" if prio.lower() == "y" else "no"
    r["note"] = optional("Note (optional)", r["note"])
    wsave(wishes)
    print(f"updated wishlist #{r['id']}")


def cmd_wish_star(args):
    wishes = wload()
    r = find(wishes, args.id)
    r["priority"] = "no" if r["priority"] == "yes" else "yes"
    wsave(wishes)
    state = "marked as priority" if r["priority"] == "yes" else "unmarked"
    print(f"wishlist #{r['id']} {r['artist']} - {r['album']} {state}")


def cmd_wish_rm(args):
    wishes = wload()
    r = find(wishes, args.id)
    if input(f"Remove wishlist #{r['id']} {r['artist']} - {r['album']}? [y/N] ").lower() != "y":
        sys.exit("cancelled")
    wishes.remove(r)
    wsave(wishes)
    print("removed (ids after this one have shifted down by one)")


def cmd_wish_done(args):
    wishes = wload()
    w = find(wishes, args.id)
    rows = load()
    entry = prompt_entry(blank_entry(w["artist"], w["album"], w["note"]), rows)
    entry["id"] = len(rows) + 1
    rows.append(entry)
    save(rows)              # the log is saved first, so nothing can be lost
    wishes.remove(w)
    wsave(wishes)
    print(f"logged #{entry['id']}: {entry['artist']} - {entry['album']} "
          "(removed from the wishlist)")


def cmd_wish_pick(args):
    wishes = wload()
    if args.priority:
        wishes = [r for r in wishes if r["priority"] == "yes"]
    if not wishes:
        sys.exit("nothing to pick from (add one with: albumlog wish add)")
    table([wish_cells(random.choice(wishes))], WISH_HEADER, WISH_RIGHT)


def cmd_wish_list(args):
    wishes = wload()
    if args.priority:
        wishes = [r for r in wishes if r["priority"] == "yes"]
    if args.search:
        q = args.search.lower()
        wishes = [r for r in wishes
                  if q in " ".join((r["artist"], r["album"], r["note"])).lower()]
    if not wishes:
        sys.exit("no wishlist entries (add one with: albumlog wish add)")
    wishes = sorted(wishes, key=WISH_SORTS[args.sort], reverse=args.reverse)
    table([wish_cells(r) for r in wishes], WISH_HEADER, WISH_RIGHT)
    print(f"{len(wishes)} albums · sorted by {args.sort}")


# ---------- list ----------

def ordered(rows, key, reverse):
    return sorted(rows, key=SORTS[key], reverse=(key in DESC) != reverse)


def cmd_list(args):
    rows = load()
    if args.favorites:
        rows = [r for r in rows if r["favorite"] == "yes"]
    if args.listen:
        rows = [r for r in rows if r["listen"] == args.listen]
    if args.format:
        rows = [r for r in rows if r["format"] == args.format]
    if args.genre:
        rows = [r for r in rows if has_tag(r["genre"], args.genre)]
    if args.country:
        code = resolve_country(args.country)
        if not code:
            sys.exit(f"unknown country: {args.country}")
        rows = [r for r in rows if has_tag(r["country"], code)]
    if args.search:
        q = args.search.lower()
        rows = [r for r in rows
                if q in " ".join((r["artist"], r["album"], r["year"],
                                  r["format"], r["genre"], r["country"],
                                  country_names(r["country"]),
                                  r["note"])).lower()]
    if not rows:
        sys.exit("no entries (add one with: albumlog add)")

    interactive = sys.stdin.isatty() and sys.stdout.isatty() and not args.no_page
    key, reverse, page = args.sort, args.reverse, 0
    size = args.limit or max(5, shutil.get_terminal_size((80, 24)).lines - 9)
    keys = {"d": "date", "f": "fav", "a": "artist", "b": "album", "y": "year"}

    while True:
        rows_sorted = ordered(rows, key, reverse)
        measure = [cells(r) for r in rows_sorted]
        if not interactive:
            table(measure, HEADER, RIGHT)
            return
        pages = max(1, -(-len(rows_sorted) // size))
        page = min(page, pages - 1)
        chunk = measure[page * size:(page + 1) * size]
        direction = "descending" if (key in DESC) != reverse else "ascending"
        print(f"\n{len(rows_sorted)} entries · sorted by {key} ({direction}) · "
              f"page {page + 1}/{pages}")
        table(chunk, HEADER, RIGHT, measure=measure)
        try:
            cmd = input("[n]ext [p]rev [d]ate [f]av [a]rtist [b]album [y]ear "
                        "[r]everse [q]uit > ").strip().lower()
        except EOFError:
            return
        if cmd in ("q", "quit"):
            return
        if cmd in ("", "n"):
            page = min(page + 1, pages - 1)
        elif cmd == "p":
            page = max(page - 1, 0)
        elif cmd == "r":
            reverse, page = not reverse, 0
        elif cmd in keys:
            key, reverse, page = keys[cmd], False, 0


# ---------- summaries ----------

def emit(records, header, right, sort, reverse, desc):
    """records: list of (cells, sort_keys). Prints a sorted boxed table."""
    if not records:
        sys.exit("no entries (add one with: albumlog add)")
    records = sorted(records, key=lambda x: x[1][sort],
                     reverse=(sort in desc) != reverse)
    table([c for c, _ in records], header, right)
    print(f"{len(records)} rows · sorted by {sort}")


def stats(group):
    """Distinct albums, listens and favorite albums for a list of entries."""
    albums = {album_key(r) for r in group}
    favs = {album_key(r) for r in group if r["favorite"] == "yes"}
    return len(albums), len(group), len(favs)


def cmd_artists(args):
    groups = {}
    for r in load():
        groups.setdefault(r["artist"].casefold(), []).append(r)
    records = []
    for group in groups.values():
        name = group[0]["artist"]
        albums, listens, favs = stats(group)
        dates = [r["date"] for r in group]
        genres = parse_tags(", ".join(r["genre"] for r in group if r["genre"]))
        records.append(((name, str(albums), str(listens), str(favs),
                         min(dates), max(dates), genres),
                        {"name": name.casefold(), "albums": albums,
                         "fav": favs, "recent": max(dates)}))
    emit(records, ("Artist", "Albums", "Listens", HEART, "First", "Last", "Genres"),
         (1, 2, 3), args.sort, args.reverse, {"albums", "fav", "recent"})


def cmd_years(args):
    groups = {}
    for r in load():
        year = r["date"][:4] if args.listened else (r["year"] or "?")
        groups.setdefault(year, []).append(r)
    records = []
    for year, group in groups.items():
        albums, listens, favs = stats(group)
        records.append(((year, str(albums), str(listens), str(favs)),
                        {"year": int(year) if year.isdigit() else 0,
                         "albums": albums, "fav": favs}))
    label = "Listened" if args.listened else "Year"
    emit(records, (label, "Albums", "Listens", HEART), (1, 2, 3),
         args.sort, args.reverse, {"year", "albums", "fav"})


def cmd_tags(args):
    field = args.kind
    groups, names = {}, {}
    for r in load():
        for t in tags_of(r[field]):
            groups.setdefault(t.casefold(), []).append(r)
            names.setdefault(t.casefold(), t)
    records = []
    for k, group in groups.items():
        albums, listens, favs = stats(group)
        shown = country_label(names[k].upper()) if field == "country" else names[k]
        records.append(((shown, str(albums), str(listens), str(favs)),
                        {"name": k, "albums": albums, "fav": favs}))
    if not records:
        sys.exit(f"no {field} tags yet")
    emit(records, (field.capitalize(), "Albums", "Listens", HEART), (1, 2, 3),
         args.sort, args.reverse, {"albums", "fav"})


def top_tag(rows, field):
    """Most common tag, counted once per distinct album."""
    counts, names, seen = {}, {}, set()
    for r in rows:
        if album_key(r) in seen:
            continue
        seen.add(album_key(r))
        for t in tags_of(r[field]):
            counts[t.casefold()] = counts.get(t.casefold(), 0) + 1
            names.setdefault(t.casefold(), t)
    if not counts:
        return "-"
    k = max(counts, key=lambda x: (counts[x], x))
    shown = country_label(names[k].upper()) if field == "country" else names[k]
    return f"{shown} ({counts[k]})"


def format_counts(rows):
    """Distinct albums per format, in a fixed order."""
    parts = []
    for fmt in FORMATS:
        n = len({album_key(r) for r in rows if r["format"] == fmt})
        if n:
            parts.append(f"{fmt} {n}")
    return ", ".join(parts) or "-"


def cmd_stats(args):
    rows, wishes = load(), wload()
    albums = {album_key(r) for r in rows}
    artists = {r["artist"].casefold() for r in rows}
    favs = {album_key(r) for r in rows if r["favorite"] == "yes"}
    dates = [r["date"] for r in rows]

    table([
        ("Entries", str(len(rows))),
        ("Distinct albums", str(len(albums))),
        ("Artists", str(len(artists))),
        (f"Favorite albums {HEART}", str(len(favs))),
        ("First listens", str(sum(r["listen"] == "first" for r in rows))),
        ("Last listens", str(sum(r["listen"] == "last" for r in rows))),
        ("Albums per format", format_counts(rows)),
        ("Earliest entry", min(dates) if dates else "-"),
        ("Latest entry", max(dates) if dates else "-"),
        ("Top genre", top_tag(rows, "genre")),
        ("Top country", top_tag(rows, "country")),
    ], ("Log", "Total"), right=(1,))

    print()
    table([
        ("Albums waiting", str(len(wishes))),
        (f"Priority albums {STAR}", str(sum(w["priority"] == "yes" for w in wishes))),
        ("Oldest waiting", min((w["added"] for w in wishes), default="-")),
        ("Also in your log", str(sum(album_key(w) in albums for w in wishes))),
    ], ("Wishlist", "Total"), right=(1,))


def main():
    p = argparse.ArgumentParser(
        prog="albumlog",
        usage="albumlog [add | list | artists | years | tags | stats | fav ID | "
              "edit ID | rm ID | wish ...]",
        description="A small offline log of the albums you listen to, "
                    "with a wishlist of albums you plan to hear.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", metavar="command")

    sub.add_parser("add", help="add an entry").set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="browse entries (default)")
    ls.add_argument("-s", "--sort", choices=sorted(SORTS), default="date",
                    help="sort order (default: date, newest first)")
    ls.add_argument("-r", "--reverse", action="store_true",
                    help="reverse the sort order")
    ls.add_argument("-f", "--favorites", action="store_true",
                    help="favorites only")
    ls.add_argument("-l", "--listen", choices=["first", "last"],
                    help="only first or only last listens")
    ls.add_argument("-F", "--format", type=format_arg, metavar="FORMAT",
                    help="only this format: digital, vinyl, CD or cassette")
    ls.add_argument("-t", "--genre", metavar="GENRE",
                    help="only entries with this genre tag")
    ls.add_argument("-c", "--country", metavar="COUNTRY",
                    help="only entries with this country (code or name)")
    ls.add_argument("-g", "--search", metavar="TEXT",
                    help="search artist, album, year, format, tags and note")
    ls.add_argument("-n", "--limit", type=int, metavar="N",
                    help="rows per page (default: fits the terminal)")
    ls.add_argument("--no-page", action="store_true",
                    help="print everything once, without navigation")
    ls.set_defaults(func=cmd_list)

    ar = sub.add_parser("artists", help="summary per artist")
    ar.add_argument("-s", "--sort", default="name",
                    choices=["name", "albums", "fav", "recent"],
                    help="sort order (default: name)")
    ar.add_argument("-r", "--reverse", action="store_true",
                    help="reverse the sort order")
    ar.set_defaults(func=cmd_artists)

    yr = sub.add_parser("years", help="summary per year")
    yr.add_argument("-s", "--sort", default="year",
                    choices=["year", "albums", "fav"],
                    help="sort order (default: year, newest first)")
    yr.add_argument("-r", "--reverse", action="store_true",
                    help="reverse the sort order")
    yr.add_argument("--listened", action="store_true",
                    help="group by the year you listened, not the release year")
    yr.set_defaults(func=cmd_years)

    tg = sub.add_parser("tags", help="summary per genre, country or format")
    tg.add_argument("kind", nargs="?", choices=["genre", "country", "format"],
                    default="genre")
    tg.add_argument("-s", "--sort", default="albums",
                    choices=["name", "albums", "fav"],
                    help="sort order (default: albums, most first)")
    tg.add_argument("-r", "--reverse", action="store_true",
                    help="reverse the sort order")
    tg.set_defaults(func=cmd_tags)

    sub.add_parser("stats", help="totals for the log and the wishlist"
                   ).set_defaults(func=cmd_stats)

    for name, func, text in (("fav", cmd_fav, "toggle the favorite heart"),
                             ("edit", cmd_edit, "edit an entry"),
                             ("rm", cmd_rm, "remove an entry")):
        s = sub.add_parser(name, help=text)
        s.add_argument("id", type=int, metavar="ID")
        s.set_defaults(func=func)

    wp = sub.add_parser("wish", help="the wishlist of albums to listen to")
    wsub = wp.add_subparsers(dest="wcmd", metavar="wish command")
    wsub.add_parser("add", help="add an album").set_defaults(func=cmd_wish_add)
    wl = wsub.add_parser("list", help="show the wishlist (default)")
    wl.add_argument("-s", "--sort", choices=sorted(WISH_SORTS), default="added",
                    help="sort order (default: added, oldest first)")
    wl.add_argument("-p", "--priority", action="store_true",
                    help="priority albums only")
    wl.add_argument("-r", "--reverse", action="store_true",
                    help="reverse the sort order")
    wl.add_argument("-g", "--search", metavar="TEXT",
                    help="search artist, album and note")
    wl.set_defaults(func=cmd_wish_list)
    wk = wsub.add_parser("pick", help="pick a random album")
    wk.add_argument("-p", "--priority", action="store_true",
                    help="pick only among priority albums")
    wk.set_defaults(func=cmd_wish_pick)
    for name, func, text in (("edit", cmd_wish_edit, "edit a wishlist entry"),
                             ("star", cmd_wish_star, "toggle the priority star"),
                             ("rm", cmd_wish_rm, "remove a wishlist entry"),
                             ("done", cmd_wish_done,
                              "move an entry into the log")):
        s = wsub.add_parser(name, help=text)
        s.add_argument("id", type=int, metavar="ID")
        s.set_defaults(func=func)

    argv = sys.argv[1:]
    if argv and argv[0] == "--stats":
        argv[0] = "stats"
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help")):
        argv.insert(0, "list")
    if argv[0] == "wish" and (len(argv) == 1 or (
            argv[1] not in WISH_COMMANDS and argv[1] not in ("-h", "--help"))):
        argv.insert(1, "list")
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
