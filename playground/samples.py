"""Synthetic sample texts for the playground.

Every value here is fabricated (valid checksums where relevant, but not issued
to anyone). Synthetic-only — never paste real personal data.
"""
from __future__ import annotations

SAMPLES: dict[str, dict[str, str]] = {
    "healthcare": {
        "title": "Healthcare",
        "icon": "🏥",
        "text": (
            "تقرير طبي\n"
            "المريض: محمد بن عبدالله القحطاني\n"
            "رقم الهوية الوطنية: 1729436483\n"
            "رقم الملف الطبي: A-99231\n"
            "الجوال: +966557924695\n"
            "الملاحظات: مراجعة دورية، لا توجد مضاعفات."
        ),
    },
    "banking": {
        "title": "Banking",
        "icon": "🏦",
        "text": (
            "طلب تحويل\n"
            "العميلة: سارة بنت أحمد\n"
            "الآيبان: SA0336056712565535665936\n"
            "رقم الهوية: 1375689344\n"
            "الرقم الضريبي: 310000000000003\n"
            "الجوال: +966557225391"
        ),
    },
    "government": {
        "title": "Government",
        "icon": "🏛️",
        "text": (
            "معاملة حكومية\n"
            "رقم الهوية الوطنية: 1729436483\n"
            "رقم الإقامة: 2858137280\n"
            "العنوان الوطني: RRAD2929\n"
            "الرقم الموحد للمنشأة: 7001234567"
        ),
    },
    "hr": {
        "title": "HR",
        "icon": "👥",
        "text": (
            "ملف موظف\n"
            "الاسم: خالد بن سعد الشهري\n"
            "رقم الإقامة: 2858137280\n"
            "البريد الإلكتروني: khalid@example.com\n"
            "الجوال: +966512027353"
        ),
    },
    "support": {
        "title": "Customer Support",
        "icon": "💬",
        "text": (
            "محادثة دعم\n"
            "العميل: أرغب بتحديث بياناتي. جوالي +966557924695 "
            "وبريدي user@example.sa ورقم هويتي 1375689344. شكراً."
        ),
    },
}
