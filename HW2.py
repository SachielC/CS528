import re
import time
import numpy as np
from collections import defaultdict
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor, as_completed


BUCKET_NAME = "hw2bucketmanyrank"
PREFIX = "graph/"            
DAMPING = 0.85
CONVERGENCE = 0.005    
MAX_WORKERS = 16       


def fetch_blob_html(blob):

    try:
        return blob.name, blob.download_as_text(timeout=300)
    except Exception as e:
        print(f"FAILED {blob.name}: {e}")
        return blob.name, ""

def load_graph_from_gcs(bucket_name, prefix):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    html_blobs = [b for b in blobs if b.name.endswith(".html")]
    if not html_blobs:
        raise RuntimeError("EMPTY FOlder...")
    pages = [b.name for b in html_blobs]
    page_set = set(pages)
    outgoing = defaultdict(set)
    incoming = defaultdict(set)
    link_pattern = re.compile(r'href="([^"]+)"', re.IGNORECASE)
    print(f"Downloading {len(pages)} pages from GCS...") #Tried to do this originally locally, was super slow. Moved to GCP Compute engine. 
    start = time.time()
    
    #From ChatGPT
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_blob_html, blob): blob.name for blob in html_blobs}
        for i, future in enumerate(as_completed(futures)):
            page, html = future.result()
            for link in link_pattern.findall(html):
                if link in page_set and link != page:
                    outgoing[page].add(link)
                    incoming[link].add(page)
            if i % 500 == 0:
                print(f"Processed {i}/{len(pages)} pages...")
    print(f"All pages processed in {time.time() - start:.1f} seconds")
    return pages, outgoing, incoming


def print_degree_stats(outgoing, incoming, pages):
    out_degrees = np.array([len(outgoing.get(p, [])) for p in pages])
    in_degrees = np.array([len(incoming.get(p, [])) for p in pages])

    def stats(arr, name):
        print(f"\n{name} degree stats:")
        print(f"  min: {arr.min()}")
        print(f"  max: {arr.max()}")
        print(f"  mean: {arr.mean():.2f}")
        print(f"  median: {np.median(arr)}")
        print(f"  quintiles: {np.quantile(arr, [0.2, 0.4, 0.6, 0.8])}")

    stats(out_degrees, "Outgoing")
    stats(in_degrees, "Incoming")

def pagerank(pages, outgoing, incoming):
    N = len(pages)
    pr = {p: 1.0 / N for p in pages}
    converged = False
    iteration = 0
    while not converged:
        new_pr = {}
        total_change = 0.0
        for page in pages:
            rank_sum = sum(pr[src] / len(outgoing[src]) for src in incoming.get(page, []) if outgoing[src])
            new_pr[page] = (1 - DAMPING) / N + DAMPING * rank_sum
            total_change += abs(new_pr[page] - pr[page])
        pr = new_pr
        iteration += 1
        print(f"Iteration {iteration}, total change = {total_change:.6f}")
        if total_change < CONVERGENCE:
            converged = True

    return pr


def main():
    print("Loading graph from GCS...")
    pages, outgoing, incoming = load_graph_from_gcs(BUCKET_NAME, PREFIX)
    print("\nComputing degree statistics...")
    print_degree_stats(outgoing, incoming, pages)
    print("\nRunning PageRank...")
    pr = pagerank(pages, outgoing, incoming)
    print("\nTop 10 pages by PageRank:")
    for page, score in sorted(pr.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{page}: {score:.6f}")

# Testing func! :)
def test_pagerank_small_graph():
    pages = ["A", "B", "C"]
    outgoing = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    incoming = {"B": {"A"}, "C": {"B"}, "A": {"C"}}
    pr = pagerank(pages, outgoing, incoming)
    for p in pages:
        print(f"{p}: {pr[p]:.4f}")

if __name__ == "__main__":
    main()
    # test_pagerank_small_graph()
