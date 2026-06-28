# Presidio integration

If you already use [Microsoft Presidio](https://microsoft.github.io/presidio/),
add Tabayyan's **validated** Saudi/Arabic recognizers with one import. The
extra is optional:

```bash
pip install "tabayyan[presidio]"
```

```python
from presidio_analyzer import AnalyzerEngine
from tabayyan.integrations.presidio import register_saudi_recognizers

analyzer = AnalyzerEngine()
register_saudi_recognizers(analyzer)   # adds SA_NATIONAL_ID, SA_IQAMA, SA_IBAN,
                                       # SA_CR, SA_PHONE_NUMBER, MEDICAL_RECORD_NUMBER,
                                       # PERSON (Arabic names)
analyzer.analyze(text="national ID 1158813996", language="en")
```

It **complements** Presidio: it adds the Saudi/Arabic entities Presidio lacks
and does not duplicate Presidio's email/credit-card/IP recognizers. Detection
is identical to the standalone library (same DetectionEngine), so checksum
validation and Arabic handling carry over. Tabayyan confidence maps to a
Presidio score (HIGH→0.95, MEDIUM→0.6, LOW→0.4), and the original
confidence/category/notes are preserved in `recognition_metadata`.

For Arabic-language analysis (`language="ar"`), configure an Arabic NLP engine
in Presidio; the pattern-based recognizers themselves need no model.
