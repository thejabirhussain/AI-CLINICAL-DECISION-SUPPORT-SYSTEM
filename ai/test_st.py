import sys
print("Starting", flush=True)
import urllib.request
urllib.request.getproxies = lambda: {}
print("Patched getproxies", flush=True)

from sentence_transformers import SentenceTransformer
print("Imported SentenceTransformer", flush=True)

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded successfully!", flush=True)
except Exception as e:
    print("Error:", e, flush=True)
