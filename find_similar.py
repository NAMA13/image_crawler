#!/usr/bin/env python3
"""
ImCrawler Similarity Checker - Image Similarity Finder
Version: 1.3.0
"""
import cv2
import numpy as np
import os
import argparse
from tqdm import tqdm
import signal
import json
from threading import Lock

# Global shutdown flag
shutdown_flag = False

def handle_sigint(signum, frame):
    global shutdown_flag
    shutdown_flag = True
    print("\nInterrupt received, stopping... you can resume later.")

signal.signal(signal.SIGINT, handle_sigint)

# ASCII Logo
logo = r'''
.___                                         .__                  
|   |  _____    ____ _______ _____  __  _  __|  |    ____ _______ 
|   | /     \ _/ ___\\_  __ \\__  \ \ \/ \/ /|  |  _/ __ \\_  __ \
|   ||  Y Y  \\  \___ |  | \/ / __ \_\     / |  |__\  ___/ |  | \/
|___||__|_|  / \___  >|__|   (____  / \/\_/  |____/ \___  >|__|   
           \/      \/             \/                    \/        

ImCrawler Similarity Checker v1.0.2 by natig.
'''  
print(logo)

# Resume/inliers file
DATA_FILE = 'inliers.json'
lock = Lock()

def load_data(directory):
    path = os.path.join(directory, DATA_FILE)
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.load(f)
        print(f"Loaded inliers for {len(data)} images, resuming...")
        return data  # dict: filename -> inliers
    return {}  # not processed


def save_data(directory, data_map):
    path = os.path.join(directory, DATA_FILE)
    with open(path, 'w') as f:
        json.dump(data_map, f, indent=2)


def compute_orb_features(image_path):
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None or image.size == 0:
            return None, None
        orb = cv2.ORB_create()
        kp, desc = orb.detectAndCompute(image, None)
        return kp, desc
    except cv2.error as e:
        print(f"Error reading {image_path}: {e}")
        return None, None


def match_and_inliers(kp1, desc1, kp2, desc2, min_matches=10):
    if shutdown_flag or desc1 is None or desc2 is None or len(kp1) < min_matches or len(kp2) < min_matches:
        return 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(desc1, desc2)
    if len(matches) < min_matches:
        return 0
    src = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
    dst = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
    M, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(np.sum(mask)) if mask is not None else 0


def find_similar_images(directory, query_image, threshold):
    files = sorted(f for f in os.listdir(directory) if f.lower().endswith(('.png','.jpg','.jpeg')))
    data_map = load_data(directory)
    kp_q, desc_q = compute_orb_features(query_image)
    if kp_q is None:
        print(f"Error: Cannot process query image {query_image}")
        return {}

    total = len(files)
    with tqdm(total=total, desc="Processing images") as pbar:
        for fname in files:
            pbar.set_postfix({"processed": len(data_map)})
            if fname in data_map:
                pbar.update(1)
                continue
            if shutdown_flag:
                break
            path = os.path.join(directory, fname)
            kp, desc = compute_orb_features(path)
            inliers = match_and_inliers(kp_q, desc_q, kp, desc, threshold)
            data_map[fname] = inliers
            # save after each to persist
            with lock:
                save_data(directory, data_map)
            pbar.update(1)
    return data_map


def print_summary(data_map, threshold):
    total = len(data_map)
    above = {f:v for f,v in data_map.items() if v > threshold}
    print("\nSummary:")
    print(f"  Total images     : {total}")
    print(f"  Above threshold  : {len(above)}")


def main():
    parser = argparse.ArgumentParser(description="Find images similar to a query image.")
    parser.add_argument("directory", help="Directory to search")
    parser.add_argument("query", help="Query image path")
    parser.add_argument("--threshold", type=int, default=10,
                        help="Min inlier count for similarity")
    args = parser.parse_args()

    data_map = find_similar_images(args.directory, args.query, args.threshold)
    print_summary(data_map, args.threshold)
    # list results sorted
    results = sorted([(f,v) for f,v in data_map.items() if v > args.threshold], key=lambda x: x[1], reverse=True)
    if results:
        print("\nSimilar images:")
        for fname, inl in results:
            print(f"{fname}: {inl} inliers")
    else:
        print("No similar images found.")

if __name__ == '__main__':
    main()