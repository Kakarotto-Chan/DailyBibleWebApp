#!/usr/bin/env python3
"""
EMA100 crossover screener for US-listed stocks.

Finds stocks whose closing price has recently crossed ABOVE its 100-day EMA
and has stayed above it for MORE than `--min-days` but LESS than `--max-days`
consecutive trading days (default: more than 3, less than 7 -> i.e. 4, 5 or 6
days). Stocks that have been above the EMA100 for `--max-days` or more are
excluded (they crossed too long ago / are already established above the line).

This script needs live market data, so it must run in an environment with
internet access (the managed Claude Code web sandbox blocks finance hosts).

Usage:
    pip install yfinance pandas
    python tools/ema100_crossover_screener.py                 # full US universe
    python tools/ema100_crossover_screener.py --tickers AAPL MSFT NVDA
    python tools/ema100_crossover_screener.py --min-days 3 --max-days 7
    python tools/ema100_crossover_screener.py --out results.csv

Criteria implemented (defaults):
    * The latest close is ABOVE the EMA100.
    * The number of consecutive trading days the close has been above the
      EMA100 ("days_above") satisfies:  min-days < days_above < max-days.
    * This naturally excludes anything already above for >= max-days (7).
"""

import argparse
import sys
import time

import pandas as pd


def _import_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        print("Missing dependency. Run: pip install yfinance pandas",
              file=sys.stderr)
        sys.exit(1)


def fetch_us_universe():
    """Download the full list of US-listed symbols from Nasdaq Trader.

    Returns a list of common-stock tickers (test issues / ETFs filtered out as
    best as the feed allows). Falls back to an empty list on failure.
    """
    import io
    import urllib.request

    files = {
        "nasdaq": "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt",
        "other": "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt",
    }
    # HTTP mirrors are more reliable than FTP from most networks.
    http_files = {
        "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    }

    tickers = []
    for name, url in http_files.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8", "replace")
            df = pd.read_csv(io.StringIO(text), sep="|")
            df = df[:-1]  # last line is a "File Creation Time" footer
            sym_col = "Symbol" if "Symbol" in df.columns else "ACT Symbol"
            # Filter out test issues and (where flagged) ETFs.
            if "Test Issue" in df.columns:
                df = df[df["Test Issue"] != "Y"]
            if "ETF" in df.columns:
                df = df[df["ETF"] != "Y"]
            syms = (
                df[sym_col]
                .dropna()
                .astype(str)
                .str.strip()
                .tolist()
            )
            tickers.extend(s for s in syms if s and "$" not in s)
        except Exception as e:  # noqa: BLE001
            print(f"  warning: could not fetch {name} list ({url}): {e}",
                  file=sys.stderr)

    # yfinance uses '-' for class shares (e.g. BRK.B -> BRK-B)
    tickers = sorted({t.replace(".", "-") for t in tickers})
    return tickers


def days_above_ema(close: pd.Series, ema: pd.Series) -> int:
    """Count consecutive most-recent trading days where close > ema.

    Returns 0 if the latest close is not above the EMA.
    """
    above = (close > ema).to_numpy()
    if len(above) == 0 or not above[-1]:
        return 0
    count = 0
    for val in reversed(above):
        if val:
            count += 1
        else:
            break
    return count


def screen(tickers, ema_period, min_days, max_days, batch_size, period):
    """Yield dict rows for tickers matching the crossover criteria."""
    yf = _import_yfinance()
    results = []
    total = len(tickers)
    for start in range(0, total, batch_size):
        batch = tickers[start:start + batch_size]
        print(f"  [{start + 1}-{min(start + batch_size, total)}/{total}] "
              f"downloading {len(batch)} symbols...", file=sys.stderr)
        try:
            data = yf.download(
                batch,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception as e:  # noqa: BLE001
            print(f"  batch download failed: {e}", file=sys.stderr)
            time.sleep(2)
            continue

        for tk in batch:
            try:
                if len(batch) == 1:
                    close = data["Close"].dropna()
                else:
                    close = data[tk]["Close"].dropna()
            except (KeyError, TypeError):
                continue

            # Need at least ema_period bars to have a meaningful EMA.
            if len(close) < ema_period + 5:
                continue

            ema = close.ewm(span=ema_period, adjust=False).mean()
            n = days_above_ema(close, ema)

            if min_days < n < max_days:
                last_close = float(close.iloc[-1])
                last_ema = float(ema.iloc[-1])
                results.append({
                    "ticker": tk,
                    "days_above_ema100": n,
                    "last_close": round(last_close, 2),
                    "ema100": round(last_ema, 2),
                    "pct_above_ema": round((last_close / last_ema - 1) * 100, 2),
                    "last_date": close.index[-1].date().isoformat(),
                })
        time.sleep(1)  # be polite to the data provider
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tickers", nargs="*", default=None,
                    help="Explicit ticker list. Default: full US listed universe.")
    ap.add_argument("--ema-period", type=int, default=100)
    ap.add_argument("--min-days", type=int, default=3,
                    help="Strictly more than this many days above EMA (default 3).")
    ap.add_argument("--max-days", type=int, default=7,
                    help="Strictly fewer than this many days above EMA (default 7).")
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--period", default="2y",
                    help="History window to download (default 2y).")
    ap.add_argument("--out", default=None, help="Optional CSV output path.")
    args = ap.parse_args()

    if args.tickers:
        tickers = [t.upper().replace(".", "-") for t in args.tickers]
    else:
        print("Fetching US-listed universe from Nasdaq Trader...", file=sys.stderr)
        tickers = fetch_us_universe()
        if not tickers:
            print("Could not build ticker universe. Pass --tickers explicitly.",
                  file=sys.stderr)
            sys.exit(1)
    print(f"Screening {len(tickers)} tickers "
          f"(close above EMA{args.ema_period} for "
          f">{args.min_days} and <{args.max_days} consecutive days)...",
          file=sys.stderr)

    rows = screen(tickers, args.ema_period, args.min_days, args.max_days,
                  args.batch_size, args.period)
    rows.sort(key=lambda r: (r["days_above_ema100"], -r["pct_above_ema"]))

    df = pd.DataFrame(rows, columns=[
        "ticker", "days_above_ema100", "last_close", "ema100",
        "pct_above_ema", "last_date",
    ])
    print(f"\n{len(df)} matches:\n", file=sys.stderr)
    print(df.to_string(index=False))

    if args.out:
        df.to_csv(args.out, index=False)
        print(f"\nSaved to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
