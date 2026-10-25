# 📥 data/raw/

This is where your **real datasets** go (downloaded from Kaggle).

**How to get them:**
1. Create a free account at [kaggle.com](https://www.kaggle.com)
2. Search for: `tourist attractions India csv` or `India travel destinations dataset`
3. Download the CSV(s) and drop them **in this folder**

**Ideal columns:** `name, city, state, category, rating, lat, lon, avg_time_hours, entry_fee_inr`

`src/data_loader.py` automatically loads whatever CSV it finds here.
If this folder is empty, it falls back to the sample dataset in `data/sample/`.

> Note: CSVs in this folder are git-ignored (too big to commit) — that's normal.
