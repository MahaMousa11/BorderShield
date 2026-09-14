import os
import glob
import hashlib
import collections

# Expected classes
VALID_CLASSES = {0, 1, 2, 3, 4}
CLASS_NAMES = {
    0: "person",
    1: "car",
    2: "bus",
    3: "motorbike",
    4: "drone"
}

# Baseline drone annotation counts (expected minimums to ensure no drone labels were lost)
BASELINE_TRAIN_DRONE_LABELS = 1623
BASELINE_VALID_DRONE_LABELS = 307

def compute_md5(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except Exception:
        return ""

def validate():
    print("="*60)
    print("BORDER SHIELD UNIFIED DATASET VALIDATION REPORT")
    print("="*60)
    
    # Base paths on Jetson Nano
    DATA_DIR = "/home/jiacdi/darknet/data"
    
    # Lists
    train_txt = os.path.join(DATA_DIR, "train_unified.txt")
    valid_txt = os.path.join(DATA_DIR, "valid_unified.txt")
    
    errors = []
    
    # 1. Verify train_unified.txt and valid_unified.txt exist
    for f_txt in [train_txt, valid_txt]:
        if not os.path.exists(f_txt):
            errors.append(f"List file does not exist: {f_txt}")
            
    if errors:
        print("CRITICAL ERRORS FOUND:")
        for err in errors:
            print(f" - {err}")
        return False
        
    # Read image paths
    def read_image_paths(filepath):
        paths = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    p = line.strip()
                    if p:
                        if not p.startswith("/"):
                            abs_p = os.path.join("/home/jiacdi/darknet", p)
                        else:
                            abs_p = p
                        paths.append((p, abs_p))
        except Exception as e:
            errors.append(f"Failed to read list file {filepath}: {e}")
        return paths

    train_images = read_image_paths(train_txt)
    valid_images = read_image_paths(valid_txt)
    
    print(f"List train_unified.txt contains {len(train_images)} images.")
    print(f"List valid_unified.txt contains {len(valid_images)} images.")
    
    # 2. Check existence of images in the list files
    for ref_path, abs_path in train_images + valid_images:
        if not os.path.exists(abs_path):
            errors.append(f"Listed image file not found: {ref_path} (resolved: {abs_path})")

    # 3. Check folder files: images vs labels match
    splits = ["train", "valid"]
    all_images_in_dir = []
    all_labels_in_dir = []
    
    image_to_label_map = {}
    label_to_image_map = {}
    
    for split in splits:
        img_dir = os.path.join(DATA_DIR, f"images/{split}")
        lbl_dir = os.path.join(DATA_DIR, f"labels/{split}")
        
        # Check directories exist
        if not os.path.exists(img_dir):
            errors.append(f"Image directory does not exist: {img_dir}")
            continue
        if not os.path.exists(lbl_dir):
            errors.append(f"Label directory does not exist: {lbl_dir}")
            continue
            
        imgs = glob.glob(os.path.join(img_dir, "*"))
        lbls = glob.glob(os.path.join(lbl_dir, "*.txt"))
        
        all_images_in_dir.extend(imgs)
        all_labels_in_dir.extend(lbls)
        
        # Map basenames
        img_basenames = {os.path.splitext(os.path.basename(x))[0]: x for x in imgs}
        lbl_basenames = {os.path.splitext(os.path.basename(x))[0]: x for x in lbls}
        
        # Verify 1-to-1 match
        for base, path in img_basenames.items():
            if base not in lbl_basenames:
                errors.append(f"Image {path} has no matching label file.")
            else:
                image_to_label_map[path] = lbl_basenames[base]
                
        for base, path in lbl_basenames.items():
            if base not in img_basenames:
                errors.append(f"Label file {path} has no matching image file.")
            else:
                label_to_image_map[path] = img_basenames[base]

    print(f"Found {len(all_images_in_dir)} total image files across directories.")
    print(f"Found {len(all_labels_in_dir)} total label files across directories.")
    
    # 4. Duplicate detections using MD5
    image_md5s = collections.defaultdict(list)
    label_md5s = collections.defaultdict(list)
    
    for img_path in all_images_in_dir:
        md5 = compute_md5(img_path)
        if md5:
            image_md5s[md5].append(img_path)
        
    for lbl_path in all_labels_in_dir:
        md5 = compute_md5(lbl_path)
        if md5:
            label_md5s[md5].append(lbl_path)
        
    # Report duplicates
    dup_images_count = 0
    for md5, paths in image_md5s.items():
        if len(paths) > 1:
            dup_images_count += (len(paths) - 1)
            
    dup_labels_count = 0
    for md5, paths in label_md5s.items():
        if len(paths) > 1:
            if os.path.getsize(paths[0]) > 0:
                dup_labels_count += (len(paths) - 1)
                
    print(f"Detected duplicate images (by MD5): {dup_images_count}")
    print(f"Detected duplicate labels (by MD5, non-empty): {dup_labels_count}")
    
    # 5. Label formatting and class distributions
    class_distribution = collections.Counter()
    drone_train_labels_count = 0
    drone_valid_labels_count = 0
    
    for lbl_path in all_labels_in_dir:
        # Check size / empty file
        if os.path.getsize(lbl_path) == 0:
            errors.append(f"Label file is empty: {lbl_path}")
            continue
            
        is_train_split = "/train/" in lbl_path
        
        with open(lbl_path, 'r') as f:
            line_num = 0
            for line in f:
                line_num += 1
                stripped = line.strip()
                if not stripped:
                    continue
                parts = stripped.split()
                if len(parts) != 5:
                    errors.append(f"YOLO format error in {lbl_path} line {line_num}: Expected 5 values, got {len(parts)} ('{stripped}')")
                    continue
                    
                # Parse class ID
                try:
                    cls_id = int(parts[0])
                except ValueError:
                    errors.append(f"Class ID format error in {lbl_path} line {line_num}: Class ID must be integer, got '{parts[0]}'")
                    continue
                    
                if cls_id not in VALID_CLASSES:
                    errors.append(f"Invalid class ID in {lbl_path} line {line_num}: Class ID {cls_id} not in range [0-4]")
                    
                # Parse bounding box floats
                bbox_vals = []
                for val_str in parts[1:]:
                    try:
                        val = float(val_str)
                        bbox_vals.append(val)
                    except ValueError:
                        errors.append(f"Bounding box value format error in {lbl_path} line {line_num}: Expected float, got '{val_str}'")
                        break
                        
                if len(bbox_vals) == 4:
                    # Verify coordinates in [0, 1]
                    for idx, val in enumerate(bbox_vals):
                        coord_name = ["x_center", "y_center", "width", "height"][idx]
                        if val < 0.0 or val > 1.0:
                            errors.append(f"Coordinate range error in {lbl_path} line {line_num}: Bounding box {coord_name} {val} outside [0, 1] range")
                            
                # Accumulate statistics
                class_distribution[cls_id] += 1
                if cls_id == 4:
                    if is_train_split:
                        drone_train_labels_count += 1
                    else:
                        drone_valid_labels_count += 1
                        
    # Print class distribution statistics
    print("\nClass Distribution Statistics:")
    for cid in sorted(CLASS_NAMES.keys()):
        count = class_distribution[cid]
        name = CLASS_NAMES[cid]
        print(f"  Class {cid} ({name}): {count} instances")
        
    # 6. Verify drone dataset is intact
    print(f"\nDrone label verification:")
    print(f"  Drone train annotations found: {drone_train_labels_count} (Expected baseline: {BASELINE_TRAIN_DRONE_LABELS})")
    print(f"  Drone valid annotations found: {drone_valid_labels_count} (Expected baseline: {BASELINE_VALID_DRONE_LABELS})")
    
    if drone_train_labels_count < BASELINE_TRAIN_DRONE_LABELS:
        errors.append(f"Drone train labels lost: Found {drone_train_labels_count}, expected at least {BASELINE_TRAIN_DRONE_LABELS}")
    if drone_valid_labels_count < BASELINE_VALID_DRONE_LABELS:
        errors.append(f"Drone valid labels lost: Found {drone_valid_labels_count}, expected at least {BASELINE_VALID_DRONE_LABELS}")

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    if errors:
        print(f"FAILED: Found {len(errors)} validation errors!")
        # Print first 20 errors to avoid flooding
        for err in errors[:20]:
            print(f" ERROR: {err}")
        if len(errors) > 20:
            print(f" ... and {len(errors) - 20} more errors.")
        return False
    else:
        print("PASSED: All validation checks completed successfully. Dataset is fully correct.")
        return True

if __name__ == '__main__':
    validate()
