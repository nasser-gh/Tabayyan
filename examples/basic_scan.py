"""Minimal usage example. Runs fully offline.

All values are SYNTHETIC — generated to satisfy their checksums for
demonstration only. They are not real and belong to no one.
"""
from tabayyan import RedactionMode, scan, scan_and_redact

SAMPLE = (
    "Patient contact: call +966545568151 or analyst@example.gov.sa. "
    "MRN: A0099231. National ID 1158813996 on file. "
    "Refund to SA9886987973091141707536."
)

print("Input:\n ", SAMPLE, "\n")

print("Findings:")
for m in scan(SAMPLE):
    print(f"  {m.entity_type.value:22} {m.confidence.value:6} {m.category.value:18} -> {m.redacted()}")

print("\nRedacted (mask):")
print(" ", scan_and_redact(SAMPLE, RedactionMode.MASK).text)

print("\nRedacted (partial, keep last 4):")
print(" ", scan_and_redact(SAMPLE, RedactionMode.PARTIAL, partial_keep_last=4).text)
