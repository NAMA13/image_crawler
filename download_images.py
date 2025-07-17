import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import concurrent.futures
import csv
from tqdm import tqdm
from collections import defaultdict

def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except Exception:
        return False

def parse_website(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        img_tags = soup.find_all('img')
        image_urls = [(urljoin(url, img['src']), url) for img in img_tags if img.get('src')]
        return image_urls
    except Exception as e:
        print(f"Failed to parse {url}: {e}")
        return []

def main(url_list_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Read the list of websites
    with open(url_list_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    all_image_urls = []
    
    # Concurrently parse websites with a progress bar
    print("Starting website parsing...")
    with tqdm(total=len(urls), desc="Parsing websites", unit="site") as parse_pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(parse_website, url) for url in urls]
            for future in concurrent.futures.as_completed(futures):
                try:
                    image_urls = future.result()
                    all_image_urls.extend(image_urls)
                    parse_pbar.update(1)
                except Exception as e:
                    print(f"Error: {e}")
                    parse_pbar.update(1)
    
    # Deduplicate image URLs
    image_to_pages = defaultdict(list)
    for img_url, page_url in all_image_urls:
        image_to_pages[img_url].append(page_url)
    
    print(f"Total unique images to download: {len(image_to_pages)}")
    
    # Download unique images with enhanced progress bar
    metadata = []
    failed_downloads = 0
    with tqdm(total=len(image_to_pages), desc="Downloading images", unit="image") as download_pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i, img_url in enumerate(image_to_pages.keys()):
                filename = f"image_{i:06d}.jpg"
                save_path = os.path.join(output_dir, filename)
                future = executor.submit(download_image, img_url, save_path)
                futures.append((future, filename, img_url, image_to_pages[img_url]))
            for future, filename, img_url, page_urls in futures:
                if future.result():
                    for page_url in page_urls:
                        metadata.append((filename, img_url, page_url))
                else:
                    failed_downloads += 1
                download_pbar.update(1)
    
    # Save metadata to CSV
    with open(os.path.join(output_dir, 'metadata.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['filename', 'image_url', 'page_url'])
        for row in metadata:
            writer.writerow(row)
    
    print(f"Download complete! Failed downloads: {failed_downloads}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python download_images.py <url_list_file> <output_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
