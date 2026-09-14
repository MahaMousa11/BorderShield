import glob
import collections

def check():
    train_txt = glob.glob('/home/jiacdi/darknet/data/labels/train/*.txt')
    valid_txt = glob.glob('/home/jiacdi/darknet/data/labels/valid/*.txt')
    
    print(f"Found {len(train_txt)} train labels and {len(valid_txt)} valid labels.")
    
    train_classes = collections.Counter()
    for f in train_txt:
        with open(f, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if parts:
                    train_classes[parts[0]] += 1
                    
    valid_classes = collections.Counter()
    for f in valid_txt:
        with open(f, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if parts:
                    valid_classes[parts[0]] += 1
                    
    print("Train unique classes and counts:", dict(train_classes))
    print("Valid unique classes and counts:", dict(valid_classes))

if __name__ == '__main__':
    check()
