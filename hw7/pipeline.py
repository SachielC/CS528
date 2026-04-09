import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, WorkerOptions
import re
import os

BUCKET_NAME = os.getenv("BUCKET_NAME")

# ---------------- PIPELINE OPTIONS ----------------
options = PipelineOptions(
    runner='DataflowRunner',
    project='coral-mission-485618-m4',
    region='us-central1',
    job_name='beam-html-analysis',
    temp_location=f'gs://{BUCKET_NAME}/tmp/',
    staging_location=f'gs://{BUCKET_NAME}/staging/',
)

# Use small machine to avoid quota issues
worker_options = options.view_as(WorkerOptions)
worker_options.machine_type = "e2-micro"
worker_options.num_workers = 1
worker_options.max_num_workers = 1

# ---------------- HELPER FUNCTIONS ----------------
def extract_links(line):
    # ✅ FIX: case-insensitive match
    return re.findall(r'href="([^"]+)"', line, re.IGNORECASE)

def extract_words(line):
    return re.findall(r'\w+', line.lower())

class GenerateBigrams(beam.DoFn):
    def process(self, words):
        for i in range(len(words) - 1):
            yield f"{words[i]} {words[i+1]}"

# ---------------- PIPELINE ----------------
with beam.Pipeline(options=options) as p:

    # ✅ Correct file reading
    lines = p | "Read HTML files" >> beam.io.ReadFromText(f"gs://{BUCKET_NAME}/*.html")

    # ---------------- OUTGOING LINKS ----------------
    outgoing = (
        lines
        | "Extract outgoing" >> beam.FlatMap(extract_links)
        | "Count outgoing" >> beam.combiners.Count.PerElement()
        | "Top outgoing" >> beam.combiners.Top.Of(5, key=lambda x: x[1])
    )

    outgoing | "Write outgoing" >> beam.io.WriteToText(
        f"gs://{BUCKET_NAME}/output/outgoing_links",
        file_name_suffix=".txt"
    )

    # ---------------- INCOMING LINKS ----------------
    incoming = (
        lines
        | "Extract incoming pairs" >> beam.FlatMap(
            lambda line: [(link, 1) for link in extract_links(line)]
        )
        | "Count incoming" >> beam.CombinePerKey(sum)
        | "Top incoming" >> beam.combiners.Top.Of(5, key=lambda x: x[1])
    )

    incoming | "Write incoming" >> beam.io.WriteToText(
        f"gs://{BUCKET_NAME}/output/incoming_links",
        file_name_suffix=".txt"
    )

    # ---------------- BIGRAMS ----------------
    bigrams = (
        lines
        | "Extract words" >> beam.Map(extract_words)
        | "Generate bigrams" >> beam.ParDo(GenerateBigrams())
        | "Count bigrams" >> beam.combiners.Count.PerElement()
        | "Top bigrams" >> beam.combiners.Top.Of(5, key=lambda x: x[1])
    )

    bigrams | "Write bigrams" >> beam.io.WriteToText(
        f"gs://{BUCKET_NAME}/output/top_bigrams",
        file_name_suffix=".txt"
    )