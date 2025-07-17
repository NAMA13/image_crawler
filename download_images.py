#!/usr/bin/env python3
"""
ImCrawler - Image Crawler & Downloader
Version: 1.0.0
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


def download_image(session, url, save_path, timeout=10):
    try:
        resp = session.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)
        return True
    except Exception:
        return False


def parse_and_download(
    session, url, output_dir, downloaded_urls, index_counter, image_bar, lock
):
    """
    Parses a single URL, downloads its images immediately,
    updates shared image progress bar, and returns stats.
    """
    metadata = []
    found = downloaded = failed = 0
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        imgs = soup.find_all("img")
        found = len([img for img in imgs if img.get("src")])
        with lock:
            image_bar.total += found
            image_bar.refresh()
        for img in imgs:
            if shutdown_flag:
                break
            src = img.get("src")
            if not src:
                continue
            img_url = urljoin(url, src)
            with lock:
                if img_url in downloaded_urls:
                    continue
                downloaded_urls.add(img_url)
                local_index = next(index_counter)
            ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
            fname = f"img_{local_index:06d}{ext}"
            save_path = os.path.join(output_dir, fname)
            if download_image(session, img_url, save_path):
                metadata.append((fname, img_url, url))
                downloaded += 1
            else:
                failed += 1
            with lock:
                image_bar.update(1)
    except Exception:
        failed += 1
    return metadata, found, downloaded, failed


def load_existing_metadata(meta_path):
    downloaded = set()
    if os.path.exists(meta_path):
        with open(meta_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                downloaded.add(row["image_url"])
    return downloaded


def append_metadata(meta_path, rows):
    header = ["filename", "image_url", "page_url"]
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


if __name__ == "__main__":
    import sys, signal

    # Handle Ctrl+C
    def handle_sigint(signum, frame):
        global shutdown_flag
        shutdown_flag = True
        print("\nInterrupt received, shutting down... please wait.")

    signal.signal(signal.SIGINT, handle_sigint)

    # ASCII Logo
    logo = r"""
.___                                         .__                  
|   |  _____    ____ _______ _____  __  _  __|  |    ____ _______ 
|   | /     \ _/ ___\\_  __ \\__  \ \ \/ \/ /|  |  _/ __ \\_  __ \
|   ||  Y Y  \\  \___ |  | \/ / __ \_\     / |  |__\  ___/ |  | \/
|___||__|_|  / \___  >|__|   (____  / \/\_/  |____/ \___  >|__|   
           \/      \/             \/                    \/        

ImCrawler v1.0.2 - Multi-threaded Image Crawler by natig.
"""
    print(logo)

    if len(sys.argv) != 2:
        print("Usage: python download_images.py <url_list_file>")
        sys.exit(1)

    url_list_file = sys.argv[1]
    with open(url_list_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    if not urls:
        print("No URLs found in the list.")
        sys.exit(1)

    domain = get_domain_name(urls[0])
    output_dir = domain
    os.makedirs(output_dir, exist_ok=True)
    meta_file = os.path.join(output_dir, "metadata.csv")

    session = init_session()
    downloaded_urls = load_existing_metadata(meta_file)
    # Notify if resuming
    if downloaded_urls:
        print("Continued from past operations; skipping already-downloaded images.")

    total_sites = len(urls)
    sites_visited = total_found = total_downloaded = total_failed = 0
    lock = Lock()
    index_counter = itertools.count()

    # Progress bars
    site_bar = tqdm(total=total_sites, desc="Processing sites", unit="site")
    image_bar = tqdm(total=0, desc="Downloading images", unit="img")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4)
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
        )
        for url in urls
    ]

    try:
        for future in concurrent.futures.as_completed(futures):
            metadata, found, downloaded, failed = future.result()
            with lock:
                append_metadata(meta_file, metadata)
                sites_visited += 1
                total_found += found
                total_downloaded += downloaded
                total_failed += failed
                site_bar.update(1)
            if shutdown_flag:
                break
    finally:
        # Cancel pending
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
