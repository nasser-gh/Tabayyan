# Showcase — before / after

Real output of `examples/showcase.py` (all values synthetic).

```text
$ python examples/showcase.py

==== INPUT (mixed Arabic/Latin, Arabic-Indic digits) ====
اسم المريض عبدالله القحطاني، الهوية ١١٥٨٨١٣٩٩٦، جوال +966512345678، الآيبان SA9886987973091141707536، MRN: A0099231، بطاقة 4111111111111111

==== DETECTION ====
  arabic_name            low    person               [عبدالله القحطاني]
  saudi_national_id      high   national_identifier  [1158813996]
  saudi_mobile           medium contact              [+966512345678]
  saudi_iban             high   financial            [SA9886987973091141707536]
  medical_record_number  low    sensitive_health     [A0099231]
  credit_card            high   financial            [4111111111111111]

==== REDACT — mask ====
اسم المريض [ARABIC_NAME]، الهوية [SAUDI_NATIONAL_ID]، جوال [SAUDI_MOBILE]، الآيبان [SAUDI_IBAN]، MRN: [MEDICAL_RECORD_NUMBER]، بطاقة [CREDIT_CARD]

==== REDACT — partial (keep last 4) ====
اسم المريض ************طاني، الهوية ******3996، جوال *********5678، الآيبان ********************7536، MRN: ****9231، بطاقة ************1111

==== REDACT — tokenize (reversible) + restore ====
redacted:  اسم المريض <ARABIC_NAME_1>، الهوية <SAUDI_NATIONAL_ID_1>، جوال <SAUDI_MOBILE_1>، الآيبان <SAUDI_IBAN_1>، MRN: <MEDICAL_RECORD_NUMBER_1>، بطاقة <CREDIT_CARD_1>
restored == original: True

==== MIDDLEWARE — Azure endpoint (cross-border) vs in-Kingdom ====
  azure.com   -> cross_border=True, health=True
  *.health.sa -> cross_border=False, in_kingdom=True
  audit (azure): {"timestamp": "2026-06-26T15:01:45+0000", "destination": "https://contoso.openai.azure.com", "destination_host": "contoso.openai.azure.com", "in_kingdom": false ...
```
