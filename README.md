# Image Finder and Downloader

This project provides two Python tools for working with images:
1. **`find_similar.py`**: A tool to search a directory for images similar to a given query image, using ORB feature matching and homography to handle cases where the query image may be a crop of a larger image.
2. **`download_images.py`**: A tool to scrape and download images from a list of websites, saving them with metadata for further analysis.

## Table of Contents
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [find_similar.py](#find_similarpy)
  - [download_images.py](#download_imagespy)
- [How It Works](#how-it-works)
  - [find_similar.py](#find_similarpy-1)
  - [download_images.py](#download_imagespy-1)
- [Contributing](#contributing)
- [License](#license)

## Requirements

The project requires the following Python packages:

opencv-python==4.12.0numpy==1.26.4tqdm==4.66.5requests==2.32.3beautifulsoup4==4.12.3

These are listed in the `requirements.txt` file for easy installation.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/image-finder-downloader.git
   cd image-finder-downloader


Set up a virtual environment (recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install dependencies:
pip install -r requirements.txt


Verify installation:Ensure you have Python 3.8+ installed. Run python3 --version to check.


Usage
find_similar.py
This script searches a directory for images similar to a query image, using ORB feature matching and homography to detect similarities, including cases where the query is a cropped portion of another image.
Command:
python3 find_similar.py <directory> <query_image> [--threshold <int>]


<directory>: Path to the folder containing images to search (e.g., ./images).
<query_image>: Path to the query image (e.g., ./b.jpg).
--threshold: Minimum number of inliers for a match (default: 10).

Example:
python3 find_similar.py images ./b.jpg --threshold 10

Output:

A progress bar shows processing status, including the most similar image found and images per second.
Example:Processing images:  35%|█████ | 1953/5529 [04:08<07:35,  7.85it/s, most_similar=image_003543.jpg, inliers=12]


Final output lists similar images:Similar images found:
image_003543.jpg: 12 inliers
image_001234.jpg: 11 inliers



download_images.py
This script downloads images from a list of websites provided in a text file and saves metadata (filename, image URL, page URL) to a CSV file.
Command:
python3 download_images.py <url_list_file> <output_dir>


<url_list_file>: Path to a text file containing website URLs (one per line).
<output_dir>: Directory to save downloaded images and metadata CSV.

Example:
python3 download_images.py urls.txt images

Output:

Progress bars for parsing websites and downloading images.
Example:Parsing websites: 100%|██████████| 10/10 [00:05<00:00,  2.00site/s]
Total unique images to download: 123
Downloading images: 100%|██████████| 123/123 [00:10<00:00, 12.30image/s]
Download complete! Failed downloads: 2


Creates images/metadata.csv with columns: filename, image_url, page_url.

How It Works
find_similar.py

Purpose: Finds images in a directory that are similar to a query image, including cases where the query is a crop of a larger image.
Method: Uses ORB (Oriented FAST and Rotated BRIEF) feature detection and homography estimation to match images.
ORB detects keypoints and descriptors in grayscale images.
Features are matched using a Brute-Force matcher with Hamming distance.
Homography (via RANSAC) identifies inliers to measure similarity, robust to cropping, scaling, or rotation.


Error Handling: Skips invalid or corrupted images with clear error messages, ensuring the script doesn’t crash.
Progress: A tqdm progress bar displays the number of images processed, processing speed, and the most similar image found so far.

download_images.py

Purpose: Scrapes and downloads images from a list of websites, deduplicates them, and saves metadata.
Method:
Parses each website using BeautifulSoup to extract <img> tag URLs.
Deduplicates image URLs to avoid redundant downloads.
Downloads images concurrently using requests and saves them as image_XXXXXX.jpg.
Saves metadata (filename, image URL, page URL) to metadata.csv.


Concurrency: Uses ThreadPoolExecutor for efficient parsing and downloading.
Progress: Shows progress bars for parsing and downloading phases, with counts of failed downloads.

Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a feature branch (git checkout -b feature-name).
Commit changes (git commit -m 'Add feature').
Push to the branch (git push origin feature-name).
Open a pull request.

Fikir babasi: Rafig Zarbaliyev

Please include tests and update the README if necessary.
License
This project is licensed under the MIT License. See the LICENSE file for details.```
