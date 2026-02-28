import sys
import os
print("Started", flush=True)
try:
    from datasets import load_dataset
    print("Imported datasets", flush=True)
    d = load_dataset('keivalya/MedQuad-MedicalQnADataset', split='train')
    print("Dataset loaded, length:", len(d), flush=True)
except Exception as e:
    print("Error:", e, flush=True)
