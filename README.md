# albumlog

A small offline album log for the terminal, like a personal, private anti-RateYourMusic. It keeps two plain text files: the albums you listened to, and a wishlist of albums you plan to hear. No account, no network and no dependencies besides Python.

## Features

- Log albums with year, first or last listen, favorite ♥, format, genres, countries and a note.
- Boxed, paged tables with sorting and filters.
- Fuzzy country picker with fzf. Only ISO 3166-1 alpha-2 codes are saved.
- A wishlist with a priority ★, a random pick and a one-step move into the log.
- Summaries per artist, year, genre, country and format, plus `stats`.

## Requirements

- Python 3.8 or newer (standard library only)
- Optional: [fzf](https://github.com/junegunn/fzf) for the country menu
- A UTF-8 terminal

## Install

```bash
cp albumlog.py ~/.local/bin/albumlog
chmod +x ~/.local/bin/albumlog
```

Make sure `~/.local/bin` is in your `PATH`.

## Usage

```bash
albumlog add          # log an album
albumlog              # browse the log
albumlog -f           # favorites only
albumlog -F vinyl     # only vinyl
albumlog -c japan     # only one country
albumlog artists      # summary per artist
albumlog stats        # totals for the log and the wishlist
albumlog wish add     # add to the wishlist
albumlog wish pick    # pick a random wishlist album
albumlog wish done 3  # move wishlist entry 3 into the log
```

Run `albumlog -h` for every command and option.

## Data

Files live in `~/.local/share/albumlog/`:

| File           | Content                      |
|----------------|------------------------------|
| `log.tsv`      | Albums you listened to       |
| `wishlist.tsv` | Albums you plan to listen to |

Both are tab-separated text with a header row. You can edit them by hand, open them in LibreOffice or Excel (choose Tab and UTF-8), and back them up by copying the folder.

## Good to know

- The `#` number is a row position, not a saved value. It can change after a removal, so check it before using `fav`, `edit`, `rm` or `wish star`.
- Dates are saved without a time (`YYYY-MM-DD`).

## Documentation

The full guide is in the [wiki](https://github.com/mars31heaven/albumlog/wiki).

## Examples

My own log and wishlist files are available [in this repository](https://github.com/mars31heaven/albumlog.m).
