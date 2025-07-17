#!/usr/bin/env python3
"""
ImCrawler - Image Crawler & Downloader
Version: 1.0.3
"""
import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import concurrent.futures
import csv
from tqdm import tqdm
from threading import Lock
import itertools
import argparse
import time
import logging
from PIL import Image
import hashlib
from io import BytesIO

# Global flag to signal shutdown
shutdown_flag = False


def get_domain_name(url):
    netloc = urlparse(url).netloc.lower()
    domain = netloc.split(":")[0]
    return domain.replace("www.", "") or "images"


def init_session():
    session = requests.Session()
    retries = Retry(
        total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; ImCrawler/1.0.0)"})
    return session


def hash_image_bytes(img_bytes):
    """Return SHA256 hash of image bytes for duplicate detection."""
    try:
        img = Image.open(BytesIO(img_bytes))
        img = img.convert("RGB")
        img = img.resize((64, 64))
        return hashlib.sha256(img.tobytes()).hexdigest()
    except Exception:
        return None


def download_image(session, url, save_path, timeout=10, hash_set=None, lock=None, throttle=0, auth=None):
    try:
        if throttle:
            time.sleep(throttle)
        resp = session.get(url, timeout=timeout, stream=True, auth=auth)
        resp.raise_for_status()
        img_bytes = resp.content
        img_hash = hash_image_bytes(img_bytes) if hash_set is not None else None
        if hash_set is not None and img_hash:
            with lock:
                if img_hash in hash_set:
                    return False  # Duplicate
                hash_set.add(img_hash)
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return False


def parse_and_download(
    session, url, output_dir, downloaded_urls, index_counter, image_bar, lock,
    allowed_exts, hash_set, throttle, depth, visited, auth
):
    """
    Recursively parses a URL, downloads images, and returns stats.
    """
    metadata = []
    found = downloaded = failed = 0
    if url in visited or shutdown_flag or depth < 0:
        return metadata, found, downloaded, failed
    visited.add(url)
    try:
        resp = session.get(url, timeout=10, auth=auth)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        imgs = soup.find_all("img")
        img_srcs = [img.get("src") for img in imgs if img.get("src")]
        # Filter by extension
        img_srcs = [
            src for src in img_srcs
            if any(src.lower().endswith(ext) for ext in allowed_exts)
        ]
        found = len(img_srcs)
        with lock:
            image_bar.total += found
            image_bar.refresh()
        for src in img_srcs:
            if shutdown_flag:
                break
            img_url = urljoin(url, src)
            with lock:
                if img_url in downloaded_urls:
                    continue
                downloaded_urls.add(img_url)
                local_index = next(index_counter)
            ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
            fname = f"img_{local_index:06d}{ext}"
            save_path = os.path.join(output_dir, fname)
            if download_image(session, img_url, save_path, hash_set=hash_set, lock=lock, throttle=throttle, auth=auth):
                metadata.append((fname, img_url, url))
                downloaded += 1
            else:
                failed += 1
            with lock:
                image_bar.update(1)
        # Recursive crawling
        if depth > 0:
            links = [a.get("href") for a in soup.find_all("a", href=True)]
            for link in links:
                next_url = urljoin(url, link)
                if urlparse(next_url).netloc == urlparse(url).netloc:
                    m, f, d, fa = parse_and_download(
                        session, next_url, output_dir, downloaded_urls, index_counter,
                        image_bar, lock, allowed_exts, hash_set, throttle, depth-1, visited, auth
                    )
                    metadata.extend(m)
                    found += f
                    downloaded += d
                    failed += fa
    except Exception as e:
        failed += 1
        logging.error(f"Failed to parse {url}: {e}")
    return metadata, found, downloaded, failed


def load_existing_metadata(meta_path):
    downloaded = set()
    if os.path.exists(meta_path):
        with open(meta_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                downloaded.add(row["image_url"])
    return downloaded


def load_existing_hashes(meta_path):
    hashes = set()
    if os.path.exists(meta_path):
        with open(meta_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "img_hash" in row:
                    hashes.add(row["img_hash"])
    return hashes


def append_metadata(meta_path, rows):
    header = ["filename", "image_url", "page_url", "img_hash"]
    new_file = not os.path.exists(meta_path)
    with open(meta_path, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def print_summary(
    total_sites, sites_visited, total_found, total_downloaded, total_failed, meta_file
):
    print("\nSummary:")
    print(f"  Sites visited      : {sites_visited}/{total_sites}")
    print(f"  Total images found : {total_found}")
    print(f"  Images downloaded  : {total_downloaded}")
    print(f"  Failed downloads   : {total_failed}")
    print(f"  Metadata saved to  : {meta_file}")


def print_logo_and_version():
    logo = r"""
.___                                         .__                  
|   |  _____    ____ _______ _____  __  _  __|  |    ____ _______ 
|   | /     \ _/ ___\\_  __ \\__  \ \ \/ \/ /|  |  _/ __ \\_  __ \
|   ||  Y Y  \\  \___ |  | \/ / __ \_\     / |  |__\  ___/ |  | \/
|___||__|_|  / \___  >|__|   (____  / \/\_/  |____/ \___  >|__|   
           \/      \/             \/                    \/        

ImCrawler Similarity Checker v1.0.3 by natig.          
    """
    print(logo)
    print("ImCrawler - Image Crawler & Downloader")
    print("Version: 1.0.3\n")


def main():
    parser = argparse.ArgumentParser(description="ImCrawler - Image Crawler & Downloader")
    parser.add_argument("url_list_file", help="File containing list of URLs")
    parser.add_argument("-o", "--output", default=None, help="Output directory")
    parser.add_argument("-t", "--threads", type=int, default=os.cpu_count() or 4, help="Number of threads")
    parser.add_argument("-e", "--ext", nargs="+", default=[".jpg", ".jpeg", ".png", ".gif"], help="Allowed image extensions")
    parser.add_argument("-d", "--depth", type=int, default=0, help="Recursive crawl depth (0 = no recursion)")
    parser.add_argument("--throttle", type=float, default=0, help="Seconds to wait between downloads")
    parser.add_argument("--username", help="HTTP Basic Auth username")
    parser.add_argument("--password", help="HTTP Basic Auth password")
    parser.add_argument("--log", default="crawler.log", help="Log file path")
    args = parser.parse_args()

    print_logo_and_version()

    logging.basicConfig(filename=args.log, level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.info("ImCrawler started.")

    with open(args.url_list_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    if not urls:
        print("No URLs found in the list.")
        sys.exit(1)

    domain = get_domain_name(urls[0])
    output_dir = args.output or domain
    os.makedirs(output_dir, exist_ok=True)
    meta_file = os.path.join(output_dir, "metadata.csv")

    # Welcome back message if resuming
    resuming = os.path.exists(meta_file) and os.path.getsize(meta_file) > 0
    if resuming:
        print("Welcome back! Resuming from previous operation...\n")

    session = init_session()
    downloaded_urls = load_existing_metadata(meta_file)
    hash_set = set()
    lock = Lock()
    index_counter = itertools.count()
    visited = set()
    auth = (args.username, args.password) if args.username and args.password else None

    # Resume: load hashes if present
    if os.path.exists(meta_file):
        with open(meta_file, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "img_hash" in row:
                    hash_set.add(row["img_hash"])

    # Progress bars
    total_sites = len(urls)
    sites_visited = total_found = total_downloaded = total_failed = 0
    site_bar = tqdm(total=total_sites, desc="Processing sites", unit="site")
    image_bar = tqdm(total=0, desc="Downloading images", unit="img")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.threads)
    futures = [
        executor.submit(
            parse_and_download,
            session,
            url,
            output_dir,
            downloaded_urls,
            index_counter,
            image_bar,
            lock,
            args.ext,
            hash_set,
            args.throttle,
            args.depth,
            visited,
            auth,
        )
        for url in urls
    ]

    try:
        for future in concurrent.futures.as_completed(futures):
            metadata, found, downloaded, failed = future.result()
            with lock:
                # Add hash to metadata
                meta_rows = []
                for fname, img_url, page_url in metadata:
                    img_path = os.path.join(output_dir, fname)
                    try:
                        with open(img_path, "rb") as f:
                            img_hash = hash_image_bytes(f.read())
                    except Exception:
                        img_hash = ""
                    meta_rows.append((fname, img_url, page_url, img_hash))
                append_metadata(meta_file, meta_rows)
                sites_visited += 1
                total_found += found
                total_downloaded += downloaded
                total_failed += failed
                site_bar.update(1)
            if shutdown_flag:
                break
    finally:
        for f in futures:
            f.cancel()
        executor.shutdown(wait=False)
        site_bar.close()
        image_bar.close()
        print_summary(
            total_sites,
            sites_visited,
            total_found,
            total_downloaded,
            total_failed,
            meta_file,
        )
        logging.info("ImCrawler finished.")

if __name__ == "__main__":
    import sys, signal

    # Handle Ctrl+C
    def handle_sigint(signum, frame):
        global shutdown_flag
        shutdown_flag = True
        print("\nInterrupt received, shutting down... please wait.")

    signal.signal(signal.SIGINT, handle_sigint)
    main()
