import glob
import os

def shift():
    train_txt = glob.glob('/home/jiacdi/darknet/data/labels/train/*.txt')
    valid_txt = glob.glob('/home/jiacdi/darknet/data/labels/valid/*.txt')
    
    all_files = train_txt + valid_txt
    print(f"Starting shifting class index on {len(all_files)} files...")
    
    modified_count = 0
    for f in all_files:
        lines = []
        changed = False
        with open(f, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if parts:
                    if parts[0] == '0':
                        parts[0] = '4'
                        changed = True
                    lines.append(' '.join(parts))
        if changed:
            with open(f, 'w') as file:
                file.write('\n'.join(lines) + '\n')
            modified_count += 1
            
    print(f"Shift completed. Modified {modified_count} files successfully.")

if __name__ == '__main__':
    shift()
