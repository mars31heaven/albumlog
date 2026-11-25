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

try:
    import readline  # noqa: F401  (enables arrow keys and line editing in input())
except ImportError:
    pass  # not available (for example on Windows); input() still works

FOLDER = os.path.expanduser("~/.local/share/albumlog")
DATA = os.path.join(FOLDER, "log.tsv")
WISHLIST = os.path.join(FOLDER, "wishlist.tsv")
FIELDS = ["date", "artist", "album", "year", "listen", "favorite",
          "format", "genre", "country", "note"]
OLD_FIELDS = ["date", "artist", "album", "year", "listen", "favorite", "note"]
WISH_FIELDS = ["added", "artist", "album", "priority", "note"]
# Fields that describe the album itself; they are kept the same on every entry.
DETAIL_FIELDS = ["year", "favorite", "format", "genre", "country", "note"]
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
    "times": lambda r: (r["times"], r["date"], r["id"]),
}
DESC = {"date", "fav", "times"}

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
quick start:
  albumlog add          log an album (pick one you logged, or Esc for a new one)
  albumlog              browse your albums, one row each
  albumlog -s times     most logged first
  albumlog stats        totals for the log and the wishlist
  albumlog wish add     add an album to the wishlist

commands:
  add               log an album, new or already logged
  list              browse your albums in boxed tables (default command)
  edit ID           edit an entry (Enter keeps a value, "-" clears optional ones)
  fav ID            toggle the favorite heart for the whole album
  rm ID             remove one entry, or all entries of the album
  artists           summary per artist
  years             summary per release year (--listened: per listening year)
  tags [genre|country|format]
                    summary per genre, country or format
  stats             totals for the log and the wishlist (also: --stats)
  wish ...          the wishlist (see below)

how logging works:
  Log an album every time you listen to it. Each time adds one entry with
  its own date. Nothing is refused or overwritten.

  The list shows each album once. The row is the album's first entry, so
  the Date column is the first time you logged it, and the Logged column
  counts its entries. Sort with -s times (most logged first, -r reverses).
  Use --all (-a) to see every entry with its own date.

  A new album asks, in this order: artist, album, listen (f/l), year,
  favorite, format, genres, countries, note, date (default: today).

repeat listen (an album you already logged):
  albumlog add opens fzf with every logged album, for example
     Dinosaur Jr. - Dinosaur  (3x, last 2026-11-19)
  Type to search. Enter picks the album, Esc logs a new album instead.
  Without fzf, or with an empty log, you type artist and album; a match
  (capitals ignored) is treated as a repeat listen.

  Then the script:
   1. shows the saved details, the count, and the first and last dates;
   2. asks about favorite, format, genres and countries, one by one:
        Format: vinyl. Change it? [y/N]
      Enter or n keeps the saved value and skips the field; y opens the
      normal prompt with the saved value as default. Artist, album and
      year are not asked: correct them in the .tsv file, or with:
      albumlog edit ID
   3. shows the note and asks "Add a new note? [y/N]". A new note is added
      after the old one, separated by " | ". The old note is never erased;
   4. uses today's date automatically and says which time this is, for
      example: logging it for the 3rd time on 2026-11-25.
  Changed details are saved on every entry of the album, so the list never
  disagrees with itself. A note belongs to the album, not to one entry.
  wish done ID follows the same flow, without the fzf step.

fields:
  listen      f (first time you heard it) or l (heard before you logged).
              Asked for new albums only; repeat entries are saved as last.
              The list shows the listen type of the album's first entry.
  year        release year, 1000 to next year
  favorite    y or n (default n); shown as ♥
  format      digital (default), vinyl, CD, cassette:
                 digital d     vinyl v, lp     CD cd     cassette k, ca, tape
              c alone is refused because it could mean CD or cassette.
              A missing format counts as digital.
  genres      comma-separated, saved in lowercase without duplicates:
              indie rock, noise pop. Spelling matters: post-rock and
              post rock are different tags.
  countries   optional. At the prompt: y opens an fzf menu (type to search
              by name or code, Tab marks several, Enter confirms, Esc
              cancels); or type codes or names: jp, brazil; - clears; Enter
              skips or keeps. Only ISO 3166-1 alpha-2 codes are saved (JP,
              US). Tables show the name too (JP Japan). Aliases: uk, usa,
              czech republic, turkey, ivory coast. England, Scotland, Wales
              and Northern Ireland are saved as GB. Without fzf you type.
  note        free text, shared by all entries of an album
  date        YYYY-MM-DD, no time of day. To backdate an entry, use edit.
  symbols     ♥ favorite in the log      ★ priority on the wishlist

prompts:
  Arrow keys, Home/End and Up/Down history work at every prompt (needs the
  readline module, included with Python on Linux and macOS).

list:
  Options: -s date|times|artist|album|year|fav   -r reverse   -a, --all
           -f favorites   -l first|last   -F FORMAT   -t GENRE (whole tag)
           -c COUNTRY (code or name)   -g TEXT (search)   -n N   --no-page
  date, times and fav start with the newest or highest first; the others
  start A to Z or oldest first. -r flips any of them. -l filters by the
  listen type of the row shown. Filters can be combined.

  Navigation keys in a terminal (piped output prints one full table):
     n / Enter  next page        p  previous page
     d  sort by date             f  favorites first
     a  sort by artist           b  sort by album
     y  sort by year             t  most logged first
     r  reverse the current order
     q  quit

edit, fav, rm:
  The # in the normal list is the number of the album's first entry. Use
  --all to see the number of every entry.
  edit ID  asks every field, including artist, album and year, with the
           current values as defaults. The date and listen type change
           only that entry; everything else, including the names, is
           applied to every entry of the album. edit can replace the note.
  fav ID   switches the heart for every entry of the album.
  rm ID    one entry: confirm with y. Several entries: o removes only that
           one, a removes all of them, c cancels.

summaries and stats:
  artists  -s name|albums|fav|recent       years  -s year|albums|fav
  tags     -s name|albums|fav              all accept -r
  Albums are distinct albums. Listens are entries. ♥ counts distinct
  favorite albums.
  stats shows two boxes. Log: listens logged, distinct albums, artists,
  favorite albums, first and last listens, albums per format, the most
  logged album, earliest and latest dates, top genre and top country.
  Wishlist: albums waiting, priority albums, the oldest one waiting, and
  how many are already in your log.

wishlist:
  wish add          add an album (artist, album, priority, optional note)
  wish list         show the wishlist (default wish command)
  wish edit ID      edit a wishlist entry
  wish star ID      toggle the priority star
  wish rm ID        remove a wishlist entry
  wish done ID      you listened to it: log it and remove it from the list
  wish pick         pick a random album
  List options: -s added|priority|artist|album (default: added, oldest
  first)   -p priority only   -r reverse   -g TEXT search
  Pick option:  -p  pick only among priority albums
  The date added is saved automatically. Adding an album that is already on
  the wishlist is refused. If it is already in your log, you are warned and
  asked to confirm. wish done saves the log first and then removes the
  wishlist entry, so an interruption cannot lose it.

storage:
  ~/.local/share/albumlog/log.tsv        every time you logged an album
  ~/.local/share/albumlog/wishlist.tsv   albums you plan to listen to
  UTF-8, tab-separated, with a header row; one row of log.tsv is one entry.
  log.tsv columns:
     date artist album year listen favorite format genre country note
  wishlist.tsv columns:
     added artist album priority note
  Editing by hand: keep the header and one tab between values; yes/no for
  favorite and priority; first/last for listen; one of digital, vinyl, CD,
  cassette for format (lp, cd and similar spellings are corrected on load);
  uppercase country codes (JP, US); one entry per line. Entries of the same
  album are grouped by artist and album, ignoring capitals, so when you
  correct a name, change it on every row of that album.
  Writes go through a temporary file, so a crash cannot corrupt the data.
  Back up by copying the albumlog folder. To use a spreadsheet, open a
  file in LibreOffice or Excel with Tab as separator and UTF-8 encoding.

good to know:
  - IDs are row positions, not saved values. They can change after a
    removal; check the # column before using fav, edit, rm or wish star.
  - A repeat is recognized by exact artist and album name (capitals
    ignored), so a typo creates a separate album. Fix it in log.tsv.
  - Renaming an album to match another logged album merges the two.
  - No time of day, no rating, and no locking (single user).
  - ISO 3166-1 has no entries for England, Scotland, Wales or Kosovo.

examples:
  albumlog add                     log an album: pick a logged one or Esc for new
  albumlog                         browse albums, newest first
  albumlog -s times                most logged albums first
  albumlog -s times -r             least logged albums first
  albumlog --all                   every single entry, with its own date
  albumlog -f                      favorites only
  albumlog -F vinyl                only albums heard on vinyl
  albumlog -t "indie rock"         only albums with that genre
  albumlog -c japan -s year        only that country, sorted by year
  albumlog -g dinosaur             search artist, album, year, tags, note
  albumlog -l first                only albums whose first entry is a first listen
  albumlog -f -F vinyl -c jp       filters can be combined
  albumlog artists -s albums       artists with the most albums first
  albumlog years --listened        albums logged per listening year
  albumlog tags format             albums per format
  albumlog tags country            albums per country
  albumlog stats                   totals for the log and the wishlist
  albumlog fav 12                  toggle the heart on album 12
  albumlog edit 12                 edit entry 12
  albumlog rm 12                   remove entry 12, or all entries of its album
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
            str(r["times"]), r["listen"], HEART if r["favorite"] == "yes" else "",
            r["format"], r["genre"], r["country"], r["note"])


HEADER = ("#", "Date", "Artist", "Album", "Year", "Logged", "Listen", HEART,
          "Format", "Genre", "Country", "Note")
RIGHT = (0, 4, 5)

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


# ---------- albums and entries ----------

def album_key(r):
    return (r["artist"].casefold(), r["album"].casefold())


def album_entries(rows, key):
    """All entries (listens) of one album."""
    return [x for x in rows if album_key(x) == key]


def first_of(group):
    """The first entry of an album: the earliest date, then the earliest row."""
    return min(group, key=lambda x: (x["date"], x["id"]))


def with_counts(rows):
    """Add r["times"], the number of entries of the same album, to every row."""
    counts = {}
    for r in rows:
        counts[album_key(r)] = counts.get(album_key(r), 0) + 1
    for r in rows:
        r["times"] = counts[album_key(r)]
    return rows


def representatives(rows):
    """One row per album: its first entry."""
    best = {}
    for r in rows:
        k = album_key(r)
        if k not in best or (r["date"], r["id"]) < (best[k]["date"], best[k]["id"]):
            best[k] = r
    return list(best.values())


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def pick_logged(rows):
    """Browse the logged albums with fzf. Returns its entries, or None."""
    if not rows:
        return None
    if not shutil.which("fzf"):
        print("fzf not found; type artist and album instead")
        return None
    groups = {}
    for r in rows:
        groups.setdefault(album_key(r), []).append(r)
    items = sorted(groups.values(),
                   key=lambda g: (first_of(g)["artist"].casefold(),
                                  first_of(g)["album"].casefold()))
    lines = "\n".join(
        f"{i}\t{first_of(g)['artist']} - {first_of(g)['album']}  "
        f"({len(g)}x, last {max(x['date'] for x in g)})"
        for i, g in enumerate(items))
    try:
        res = subprocess.run(
            ["fzf", "--delimiter", "\t", "--with-nth", "2..",
             "--height", "40%", "--reverse", "--prompt", "Album> ",
             "--header", "Enter: album already logged | Esc: new album"],
            input=lines, stdout=subprocess.PIPE, text=True)
    except OSError:
        return None
    if res.returncode != 0 or not res.stdout.strip():
        return None
    return items[int(res.stdout.split("\t", 1)[0])]


# ---------- input ----------

def ask(label, default="", check=None):
    while True:
        shown = f" [{default}]" if default else ""
        val = clean(input(f"{label}{shown}: ")) or default
        err = check(val) if check else None
        if not err:
            return val
        print(err)


def confirm(question, default):
    """Yes/no question; Enter gives the default."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        ans = input(f"{question} {hint} ").strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("type y or n")


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


def ask_listen(default=""):
    val = ask("Listen: [f]irst or [l]ast", default[:1],
              lambda v: None if v.lower() in ("f", "l", "first", "last")
              else "type f or l")
    return "first" if val.lower().startswith("f") else "last"


def ask_favorite(current):
    fav = ask("Favorite? [y/n]", "y" if current == "yes" else "n", yes_no)
    return "yes" if fav.lower() == "y" else "no"


def ask_format(current):
    fmt = ask("Format: [d]igital, [v]inyl, [cd], [k] cassette",
              current or DEFAULT_FORMAT, check_format)
    return normalize_format(fmt)


def ask_genres(current):
    return parse_tags(
        optional("Genres, comma-separated (optional)", current), lower=True)


def prompt_details(cur):
    """Ask every album-level field, using the values in `cur` as defaults."""
    return {
        "year": ask("Year", cur["year"], check_year),
        "favorite": ask_favorite(cur["favorite"]),
        "format": ask_format(cur["format"]),
        "genre": ask_genres(cur["genre"]),
        "country": prompt_countries(cur["country"]),
        "note": optional("Note (optional)", cur["note"]),
    }


def revise_details(cur):
    """Repeat listen: offer to change each saved field; never replace the note.

    Artist, album and year are not asked; they are corrected in the .tsv file.
    """
    d = {k: cur[k] for k in DETAIL_FIELDS}

    def change(label, shown):
        return confirm(f"{label}: {shown or '-'}. Change it?", False)

    if change("Favorite", cur["favorite"]):
        d["favorite"] = ask_favorite(cur["favorite"])
    if change("Format", cur["format"]):
        d["format"] = ask_format(cur["format"])
    if change("Genres", cur["genre"]):
        d["genre"] = ask_genres(cur["genre"])
    if change("Countries", country_names(cur["country"])):
        d["country"] = prompt_countries(cur["country"])

    print(f"Note: {cur['note'] or '-'}")
    if confirm("Add a new note?", False):
        new = clean(input("New note: "))
        if new:
            d["note"] = f"{cur['note']} | {new}" if cur["note"] else new
    return d


def show_logged(group):
    """Tell the user an album is already logged and print its details."""
    base = first_of(group)
    dates = sorted(x["date"] for x in group)
    n = len(group)
    print(f"{base['artist']} - {base['album']}: already logged {n} "
          f"time{'s' if n != 1 else ''} (first {dates[0]}, last {dates[-1]}). "
          "Saved details:")
    shown = (
        ("Year", base["year"]),
        ("Favorite", base["favorite"]),
        ("Format", base["format"]),
        ("Genres", base["genre"]),
        ("Countries", country_names(base["country"])),
        ("Note", base["note"]),
    )
    for label, value in shown:
        print(f"  {label + ':':<11}{value or '-'}")


def blank_entry(artist="", album="", note=""):
    return {"id": 0, "date": date.today().isoformat(), "artist": artist,
            "album": album, "year": "", "listen": "", "favorite": "no",
            "format": "", "genre": "", "country": "", "note": note}


def log_listen(rows, artist="", album="", note=""):
    """Log one listen and append it to `rows`.

    With no artist and album given (albumlog add), fzf offers the albums
    already logged. A repeat listen shows the saved details, offers to change
    each one, keeps the old note, and uses today's date. Changed details are
    copied to every entry of that album.
    """
    group = None
    if not artist and not album:
        group = pick_logged(rows)
    if group is None:
        artist = ask("Artist", artist, need)
        album = ask("Album", album, need)
        group = album_entries(rows, (artist.casefold(), album.casefold()))

    entry = blank_entry(artist, album, note)
    if group:
        base = first_of(group)
        entry["artist"], entry["album"] = base["artist"], base["album"]
        show_logged(group)
        entry.update(revise_details(base))
        entry["listen"] = "last"
        print(f"logging it for the {ordinal(len(group) + 1)} time "
              f"on {entry['date']}")
    else:
        entry["listen"] = ask_listen()
        entry.update(prompt_details(entry))
        entry["date"] = ask("Date YYYY-MM-DD", entry["date"], check_date)

    entry["id"] = len(rows) + 1
    for x in group:
        x.update({k: entry[k] for k in DETAIL_FIELDS})
    rows.append(entry)
    return entry


# ---------- entry commands ----------

def cmd_add(args):
    rows = load()
    entry = log_listen(rows)
    save(rows)
    n = len(album_entries(rows, album_key(entry)))
    extra = f" ({ordinal(n)} time)" if n > 1 else ""
    print(f"added #{entry['id']}: {entry['artist']} - {entry['album']}{extra}")


def cmd_edit(args):
    rows = load()
    r = find(rows, args.id)
    group = album_entries(rows, album_key(r))

    new = {}
    new["artist"] = ask("Artist", r["artist"], need)
    new["album"] = ask("Album", r["album"], need)
    listen = ask_listen(r["listen"])
    new.update(prompt_details(r))
    when = ask("Date of this entry YYYY-MM-DD", r["date"], check_date)

    for x in group:          # album-level changes apply to every entry
        x.update(new)
    r["listen"], r["date"] = listen, when
    save(rows)
    extra = f" (details applied to all {len(group)} entries)" if len(group) > 1 else ""
    print(f"updated #{r['id']}{extra}")


def cmd_fav(args):
    rows = load()
    r = find(rows, args.id)
    value = "no" if r["favorite"] == "yes" else "yes"
    for x in album_entries(rows, album_key(r)):
        x["favorite"] = value
    save(rows)
    state = "marked as favorite" if value == "yes" else "unmarked"
    print(f"#{r['id']} {r['artist']} - {r['album']} {state}")


def cmd_rm(args):
    rows = load()
    r = find(rows, args.id)
    group = album_entries(rows, album_key(r))
    targets = [r]
    if len(group) > 1:
        ans = ask(f"{r['artist']} - {r['album']} has {len(group)} entries. "
                  f"Remove only #{r['id']} (o), all {len(group)} (a), "
                  "or cancel (c)", "c",
                  lambda v: None if v.lower() in ("o", "a", "c")
                  else "type o, a or c").lower()
        if ans == "c":
            sys.exit("cancelled")
        if ans == "a":
            targets = group
    elif input(f"Remove #{r['id']} {r['artist']} - {r['album']}? [y/N] "
               ).lower() != "y":
        sys.exit("cancelled")
    gone = {id(x) for x in targets}
    save([x for x in rows if id(x) not in gone])
    print(f"removed {len(targets)} entr{'y' if len(targets) == 1 else 'ies'} "
          "(ids after the removed ones have shifted down)")


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
    entry = log_listen(rows, w["artist"], w["album"], w["note"])
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
    rows = with_counts(load())
    if not args.all:
        rows = representatives(rows)   # one row per album: its first entry
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

    unit = "entries" if args.all else "albums"
    interactive = sys.stdin.isatty() and sys.stdout.isatty() and not args.no_page
    key, reverse, page = args.sort, args.reverse, 0
    size = args.limit or max(5, shutil.get_terminal_size((80, 24)).lines - 9)
    keys = {"d": "date", "f": "fav", "a": "artist", "b": "album",
            "y": "year", "t": "times"}

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
        print(f"\n{len(rows_sorted)} {unit} · sorted by {key} ({direction}) · "
              f"page {page + 1}/{pages}")
        table(chunk, HEADER, RIGHT, measure=measure)
        try:
            cmd = input("[n]ext [p]rev [d]ate [f]av [a]rtist [b]album [y]ear "
                        "[t]imes [r]everse [q]uit > ").strip().lower()
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


def most_logged(rows):
    counts, names = {}, {}
    for r in rows:
        k = album_key(r)
        counts[k] = counts.get(k, 0) + 1
        names.setdefault(k, f"{r['artist']} - {r['album']}")
    if not counts:
        return "-"
    k = max(counts, key=lambda x: (counts[x], x))
    return f"{names[k]} ({counts[k]})"


def cmd_stats(args):
    rows, wishes = load(), wload()
    albums = {album_key(r) for r in rows}
    artists = {r["artist"].casefold() for r in rows}
    favs = {album_key(r) for r in rows if r["favorite"] == "yes"}
    dates = [r["date"] for r in rows]

    table([
        ("Listens logged", str(len(rows))),
        ("Distinct albums", str(len(albums))),
        ("Artists", str(len(artists))),
        (f"Favorite albums {HEART}", str(len(favs))),
        ("First listens", str(sum(r["listen"] == "first" for r in rows))),
        ("Last listens", str(sum(r["listen"] == "last" for r in rows))),
        ("Albums per format", format_counts(rows)),
        ("Most logged album", most_logged(rows)),
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

    sub.add_parser("add", help="log an album (new or already logged)"
                   ).set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="browse albums (default)")
    ls.add_argument("-s", "--sort", choices=sorted(SORTS), default="date",
                    help="sort order (default: date, newest first; "
                         "times = most logged first)")
    ls.add_argument("-r", "--reverse", action="store_true",
                    help="reverse the sort order")
    ls.add_argument("-a", "--all", action="store_true",
                    help="show every entry instead of one row per album")
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
