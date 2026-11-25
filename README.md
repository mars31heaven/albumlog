# albumlog

A small offline album log for the terminal, like a personal, private anti-RateYourMusic. It keeps two plain text files: every time you listened to an album, and a wishlist of albums you plan to hear. No account, no network and no dependencies besides Python.

## Features

- Log an album every time you hear it. The list shows each album once, with a Logged count you can sort by (`albumlog -s times`).
- Fuzzy search of your logged albums when you add, so logging a repeat listen takes a few keystrokes.
- Favorite ♥, format, genres, countries and notes. A new note never erases the old one.
- Boxed, paged tables with sorting and filters.
- Fuzzy country picker with fzf. Only ISO 3166-1 alpha-2 codes are saved.
- A wishlist with a priority ★, a random pick and a one-step move into the log.
- Summaries per artist, year, genre, country and format, plus `stats`.
- Plain text files, safe writes and no dependencies besides Python.

## Requirements

- Python 3.8 or newer (standard library only)
- Recommended: [fzf](https://github.com/junegunn/fzf), for the album search and the country menu
- A UTF-8 terminal

## Install

```bash
cp albumlog.py ~/.local/bin/albumlog
chmod +x ~/.local/bin/albumlog
```

Make sure `~/.local/bin` is in your `PATH`.

## Usage

```bash
albumlog add          # log an album: Enter on a logged one, Esc for a new one
albumlog              # browse your albums
albumlog -s times     # most logged first
albumlog --all        # every single entry
albumlog -f           # favorites only
albumlog -F vinyl     # only vinyl
albumlog -c japan     # only one country
albumlog artists      # summary per artist
albumlog stats        # totals for the log and the wishlist
albumlog wish add     # add to the wishlist
albumlog wish pick    # pick a random wishlist album
albumlog wish done 3  # move wishlist entry 3 into the log
```

Run `albumlog -h` for every command, option, key and rule.

## Logging an album again

`albumlog add` opens fzf with the albums you already logged. Press Enter on one and the script:

- shows its saved details and how many times you logged it,
- asks whether to change each one: favorite, format, genres and countries (default: no, so Enter keeps the saved value),
- offers to add a new note without erasing the old one (default: no),
- uses today's date and tells you which time this is (2nd, 3rd, and so on).

Artist, album and year are not asked again. Press Esc in fzf to log a new album instead.

## Data

Files live in `~/.local/share/albumlog/`:

| File           | Content                         |
|----------------|---------------------------------|
| `log.tsv`      | Every time you logged an album  |
| `wishlist.tsv` | Albums you plan to listen to    |

Both are tab-separated UTF-8 text with a header row, and one row of `log.tsv` is one listen. You can edit them by hand (this is how you fix a wrong artist, album or year), open them in LibreOffice or Excel (choose Tab and UTF-8), and back them up by copying the folder.

## Good to know

- The `#` number is a row position, not a saved value. It can change after a removal, so check it before using `fav`, `edit`, `rm` or `wish star`.
- Repeat listens are recognized by exact artist and album name (capitals ignored), so a typo creates a separate album.
- Dates are saved without a time (`YYYY-MM-DD`). There is no rating, by design.

## Documentation

- `albumlog -h` is the quick reference in your terminal.
- The [wiki](../../wiki) is the full guide, with every field, the file format and troubleshooting.
