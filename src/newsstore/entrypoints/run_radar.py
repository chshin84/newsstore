"""로컬 작업장 CLI — sync|prices|radar|backtest. '오늘'은 여기서 KST로 한 번만 결정한다."""
from __future__ import annotations

import argparse
import pathlib


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=("sync", "prices", "radar", "backtest"))
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()
    from newsstore.radar import localdb
    pathlib.Path("data").mkdir(exist_ok=True)
    if args.mode == "sync":
        from newsstore.radar import sync
        db = localdb.connect_items("data/local.db")
        n = sync.run_sync(db)
        print(f"sync: {n}건 적재, 워터마크 {localdb.get_watermark(db)}")
    elif args.mode == "prices":
        from newsstore.radar import prices, watchlist
        db = localdb.connect_prices("data/prices.db")
        rep = prices.ingest(db, watchlist.load_watchlist())
        for t, r in rep.items():
            print(f"prices[{t}]: {r}")
    elif args.mode == "radar":
        from newsstore.radar import daily
        today = localdb.today_kst()
        items_db = localdb.connect_items("data/local.db")
        prices_db = localdb.connect_prices("data/prices.db")
        md = daily.build_report(items_db, prices_db, today=today)
        out = pathlib.Path("radar_out") / f"{today}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"radar: {out} 작성")
    else:
        from newsstore.radar import backtest
        backtest.main(as_of=args.as_of)


if __name__ == "__main__":
    main()
