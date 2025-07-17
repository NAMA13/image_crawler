import cv2
import numpy as np
import os
import argparse
from tqdm import tqdm

def compute_orb_features(image_path):
    """Compute ORB keypoints and descriptors for an image."""
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None, None
        # Ensure image dimensions are valid
        if image.shape[0] == 0 or image.shape[1] == 0:
            return None, None
        orb = cv2.ORB_create()
        keypoints, descriptors = orb.detectAndCompute(image, None)
        return keypoints, descriptors
    except cv2.error as e:
        print(f"Error processing {image_path}: {e}")
        return None, None

def match_features_and_find_homography(kp1, desc1, kp2, desc2, min_match_count=10):
    """Match ORB features and find homography to count inliers."""
    if desc1 is None or desc2 is None or len(kp1) < min_match_count or len(kp2) < min_match_count:
        return 0
    try:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desc1, desc2)
        if len(matches) < min_match_count:
            return 0
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if M is not None and mask is not None:
            inliers = np.sum(mask)
            return inliers
        return 0
    except cv2.error:
        return 0

def find_similar_images(directory, query_image, threshold=10):
    """Find images in a directory similar to the query image based on feature matching."""
    similar_images = []
    image_files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    query_kp, query_desc = compute_orb_features(query_image)
    if query_kp is None or query_desc is None:
        print(f"Error: Could not process query image {query_image}")
        return []
    
    most_similar = None
    max_inliers = 0
    
    with tqdm(total=len(image_files), desc="Processing images") as pbar:
        for filename in image_files:
            image_path = os.path.join(directory, filename)
            kp, desc = compute_orb_features(image_path)
            if kp is None or desc is None:
                pbar.update(1)
                continue
            inliers = match_features_and_find_homography(query_kp, query_desc, kp, desc)
            if inliers > threshold:
                similar_images.append((filename, inliers))
            if inliers > max_inliers:
                max_inliers = inliers
                most_similar = filename
            pbar.set_postfix({'most_similar': most_similar or 'None', 'inliers': max_inliers})
            pbar.update(1)
    
    return similar_images

def main():
    parser = argparse.ArgumentParser(description="Find similar images in a directory.")
    parser.add_argument("directory", help="Directory containing images to search through")
    parser.add_argument("query", help="Path to the query image")
    parser.add_argument("--threshold", type=int, default=10, 
                        help="Minimum number of inliers for similarity (default: 10)")
    args = parser.parse_args()
    
    similar_images = find_similar_images(args.directory, args.query, args.threshold)
    if similar_images:
        similar_images.sort(key=lambda x: x[1], reverse=True)
        print("\nSimilar images found:")
        for filename, inliers in similar_images:
            print(f"{filename}: {inliers} inliers")
    else:
        print("No similar images found or error with query image.")

if __name__ == "__main__":
    main()
