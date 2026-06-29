# تبيّن · Tabayyan

**كشف وتعقيم البيانات الشخصية (PII) بوعي سعودي، لمسارات نماذج اللغة (LLM). محلي بالكامل، صفر telemetry.**

[English README](README.md) · [التوثيق](docs/) · [الترخيص: Apache-2.0](LICENSE)

أدوات كشف الـ PII العامة مبنية حول المعرّفات الغربية وتفوّت السعودية—أو تعلّمها بدون تحقّق. **تبيّن** يكشف البيانات الشخصية السعودية (الهوية الوطنية، الإقامة، الآيبان السعودي، السجل التجاري، الجوال، رقم الملف الطبي) **مع تحقّق فعلي من checksum**، ثم يصنّف كل نتيجة حسب فئة البيانات ومستوى الثقة—عشان تعقّم أو تبلوك قبل ما يغادر النص بيئتك إلى أي LLM.

يعمل **offline بالكامل**: صفر اتصال خارجي، صفر telemetry، صفر dependencies في نواة الكشف.

## ليش مختلف

| | أدوات PII العامة | تبيّن |
|---|---|---|
| الهوية الوطنية / الإقامة | تُفوَّت أو بلا تحقّق | **مُتحقَّقة بالـ checksum** (HIGH) |
| الآيبان السعودي | جزئي | **ISO 13616 mod-97** (HIGH) |
| الأرقام العربية (٠-٩) | غالباً تُفوَّت | تُطبَّع وتُكشَف |
| رقم الملف الطبي | عام | فئة صحية، واعٍ بـ PDPL/NDMO |
| الأسماء العربية | غالباً تُفوَّت | كاشف heuristic |
| النطاقات المتشابهة (homoglyph) | نادر | **واعٍ بالعربي+اللاتيني** (اختياري) |
| اتصال بالشبكة | أحياناً | **أبداً** |

## التثبيت والبدء

```bash
pip install tabayyan
```
```python
from tabayyan import scan, scan_and_redact, RedactionMode

for m in scan("الهوية 1158813996، جوال +966512345678"):
    print(m.entity_type.value, m.confidence.value, m.category.value)

print(scan_and_redact("الهوية 1158813996", RedactionMode.MASK).text)
# الهوية [SAUDI_NATIONAL_ID]
```

## نموذج الثقة

- **HIGH** — ينجح في checksum منشور (الهوية، الإقامة، الآيبان، البطاقة). نسبة false positive منخفضة جداً.
- **MEDIUM** — تطابق صيغة قوي بلا checksum (جوال `+966`، إيميل).
- **LOW** — صيغة/سياق فقط، احتمال false positive معتبر (CR، MRN، الأسماء). أكّد قبل التصرف.

## Middleware و Audit (Azure / OpenAI)

حارس قدام الـ LLM endpoint: يعقّم البيانات الشخصية قبل المغادرة، ويطلع audit trail—مع **تعليم النقل خارج الحدود (cross-border)** تحت PDPL المادة 29 لأي endpoint خارج المملكة.

```python
from tabayyan import Guard, AuditLog

guard = Guard(in_kingdom_hosts=["llm.myhospital.health.sa"],
              audit=AuditLog(path="audit.jsonl"))
pr = guard.protect("الهوية 1158813996", destination="https://contoso.openai.azure.com")
pr.audit.cross_border_transfer  # True للـ endpoints الخارجية مع بيانات شخصية
```

## التكامل مع Presidio

تستخدم [Microsoft Presidio](https://microsoft.github.io/presidio/)؟ أضف كاشفات تبيّن المُتحقَّقة بسطر واحد:

```bash
pip install "tabayyan[presidio]"
```
```python
from presidio_analyzer import AnalyzerEngine
from tabayyan.integrations.presidio import register_saudi_recognizers
analyzer = AnalyzerEngine()
register_saudi_recognizers(analyzer)   # SA_NATIONAL_ID, SA_IQAMA, SA_IBAN, ...
```

## النطاق والحدود (بصدق)

تبيّن **أداة مساعِدة للكشف، مب ضمان امتثال**.

- نجاح الـ checksum يعني القيمة *صحيحة بنيوياً*، **مب** إنها صدرت فعلاً أو تخص شخصاً حقيقياً.
- خوارزمية **الهوية** هي المعيار المجتمعي (مُتحقَّقة تفاضلياً مقابل مرجع مستقل بتطابق 100%) لكنها **مب** مواصفة حكومية رسمية—تحقّق قبل الإنتاج (انظر docs/REFERENCES.md).
- **CR** و **MRN** بلا checksum عام؛ الكشف صيغة + سياق فقط. **الأسماء العربية** heuristic مب ML NER—الـ recall محدود بالتصميم لحماية الـ precision.
- توجد false negatives. لا تجعلها ضابطك الوحيد للبيانات الشخصية أو الصحية.
- المقاييس المنشورة على **بيانات synthetic**؛ لا تمثّل توزيع النصوص الواقعية.

## التحقّق المستقل

| الكاشف | المرجع المستقل |
|---|---|
| الهوية / الإقامة | alhazmy13/Saudi-ID-Validator — تطابق 100% على 50k+ |
| الآيبان | python-stdnum + أمثلة معيارية |
| البطاقة (Luhn) | python-stdnum + أرقام شبكات رسمية |

## الترخيص

[Apache-2.0](LICENSE). المساهمات مرحّب بها—قاعدة واحدة صارمة: **بيانات synthetic فقط، لا تُودِع أي بيانات شخصية حقيقية أبداً.**
