"""Before/after showcase of Tabayyan. All values are synthetic.

Run:  python examples/showcase.py
"""
from tabayyan import Guard, RedactionMode, restore, scan, scan_and_redact

SAMPLE = (
    "اسم المريض عبدالله القحطاني، الهوية ١١٥٨٨١٣٩٩٦، "
    "جوال +966512345678، الآيبان SA9886987973091141707536، "
    "MRN: A0099231، بطاقة 4111111111111111"
)


def rule(t):
    print("\n" + "=" * 4, t, "=" * 4)


rule("INPUT (mixed Arabic/Latin, Arabic-Indic digits)")
print(SAMPLE)

rule("DETECTION")
for m in scan(SAMPLE):
    print(f"  {m.entity_type.value:22} {m.confidence.value:6} {m.category.value:20} [{m.value}]")

rule("REDACT — mask")
print(scan_and_redact(SAMPLE, RedactionMode.MASK).text)

rule("REDACT — partial (keep last 4)")
print(scan_and_redact(SAMPLE, RedactionMode.PARTIAL, partial_keep_last=4).text)

rule("REDACT — tokenize (reversible) + restore")
r = scan_and_redact(SAMPLE, RedactionMode.TOKENIZE)
print("redacted: ", r.text)
print("restored == original:", restore(r.text, r.vault) == SAMPLE)

rule("MIDDLEWARE — Azure endpoint (cross-border) vs in-Kingdom")
g = Guard(in_kingdom_hosts=["llm.myhospital.health.sa"])
ext = g.protect(SAMPLE, destination="https://contoso.openai.azure.com")
ink = g.protect(SAMPLE, destination="https://llm.myhospital.health.sa/v1")
print(f"  azure.com   -> cross_border={ext.audit.cross_border_transfer}, health={ext.audit.health_data_present}")
print(f"  *.health.sa -> cross_border={ink.audit.cross_border_transfer}, in_kingdom={ink.audit.in_kingdom}")
print("  audit (azure):", ext.audit.to_json()[:160], "...")
