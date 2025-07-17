```markdown
# ImCrawler

**Version:** 1.3.0  
A pair of command‑line utilities for:

1. **Bulk downloading** images from a list of websites, with resume support.  
2. **Finding visually similar** images in a local directory via ORB feature matching, with resume & inlier persistence.

---

## 📦 Repository Contents

```


├── download\_images.py       # ImCrawler Downloader (v1.0.2)

├── find\_similar.py          # ImCrawler Similarity Checker (v1.0.2)

├── README.md                # This file

├── requirements.txt         # Python dependencies

└── examples/

├── url\_list.txt         # Example list of URLs

└── sample\_images/       # Sample directory for similarity checker

````

---

## ⚙️ Installation

1. **Clone the repo**  
   ```bash
   git clone https://github.com/yourusername/imcrawler.git
   cd imcrawler
````

2. **Set up a virtual environment** (optional, but recommended)

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > **requirements.txt** should include:
   >
   > ```
   > requests
   > beautifulsoup4
   > tqdm
   > opencv-python-headless
   > numpy
   > ```

---

## 🚀 Usage

### 1. Downloader (`download_images.py`)

Bulk‑crawl websites and download all `<img>` assets into a domain‑named folder.

```bash
python3 download_images.py url_list.txt
```

* **`url_list.txt`**
  A plain text file with one URL per line.
* **Resume support:**

  * Existing `metadata.csv` is loaded and URLs already downloaded are skipped.
  * On Ctrl+C, the script cleans up gracefully; re‑running will pick up where you left off.
* **Output:**

  * A folder named after the first URL’s domain (e.g. `example.com/`).
  * Inside: `image_XXXXX.ext` files and `metadata.csv` with columns:
    `filename, image_url, page_url`.

#### Example

```bash
# Crawl three sites, auto‑folder “example.com”
echo "https://example.com" > url_list.txt
echo "https://example.com/gallery" >> url_list.txt

python3 download_images.py url_list.txt
```

---

### 2. Similarity Checker (`find_similar.py`)

Compute ORB descriptors and RANSAC inliers to find images similar to a given query.

```bash
python3 find_similar.py <image_dir> <query_image> [--threshold N]
```

* **`<image_dir>`**
  Folder containing `.png`, `.jpg`, `.jpeg` images to scan.
* **`<query_image>`**
  Path to the image you want to compare against.
* **`--threshold N`** (default: `10`)
  Minimum number of RANSAC inliers to consider “similar.”

#### Resume & Persistence

* All processed filenames and their inlier counts are stored in `inliers.json` inside `<image_dir>`.
* On startup, existing inliers are loaded, and those images are **skipped**—so you only process new ones.
* Ctrl+C safely stops and you can rerun to continue.

#### Example

```bash
# Compare “query.jpg” against 500 downloaded images in “example.com/”
python3 find_similar.py example.com/ query.jpg --threshold 20
```

---

## 📝 Summary & Logging

Both tools print:

* **ASCII banner** with name & version.
* **TQDM progress bar** showing live progress.
* **Graceful SIGINT handling** (Ctrl+C) that stops and allows resumption.
* **End‑of‑run summary**, including counts of successes/failures or similar matches.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.

---

## 🛠️ Contributing

1. Fork the repo
2. Create a feature branch
3. Commit & push
4. Open a pull request

Feel free to report issues or propose enhancements!
