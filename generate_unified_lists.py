import os
import glob

def generate():
    data_dir = "/home/jiacdi/darknet/data"
    
    # 1. Train set
    train_imgs = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        train_imgs.extend(glob.glob(os.path.join(data_dir, "images/train", ext)))
        
    train_lines = []
    for img_path in sorted(train_imgs):
        # We need paths relative to /home/jiacdi/darknet/ (e.g. data/images/train/xyz.jpg)
        rel_p = os.path.relpath(img_path, "/home/jiacdi/darknet")
        train_lines.append(rel_p)
        
    train_txt = os.path.join(data_dir, "train_unified.txt")
    with open(train_txt, 'w') as f:
        f.write('\n'.join(train_lines) + '\n')
    print(f"Generated {train_txt} with {len(train_lines)} files.")

    # 2. Valid set
    valid_imgs = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        valid_imgs.extend(glob.glob(os.path.join(data_dir, "images/valid", ext)))
        
    valid_lines = []
    for img_path in sorted(valid_imgs):
        rel_p = os.path.relpath(img_path, "/home/jiacdi/darknet")
        valid_lines.append(rel_p)
        
    valid_txt = os.path.join(data_dir, "valid_unified.txt")
    with open(valid_txt, 'w') as f:
        f.write('\n'.join(valid_lines) + '\n')
    print(f"Generated {valid_txt} with {len(valid_lines)} files.")

if __name__ == '__main__':
    generate()
