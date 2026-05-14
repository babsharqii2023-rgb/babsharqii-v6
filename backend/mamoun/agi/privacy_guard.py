"""
BABSHARQII (Mamoun) v6.0 — Privacy Guard
حارس الخصوصية — نظام حماية البيانات الحساسة من التسرب

Implements a comprehensive privacy guard system that scans, detects, redacts,
and anonymizes sensitive information before it leaves the system. Covers PII,
financial data, credentials, medical records, location data, proprietary
research, and internal system architecture details.

Research basis:
    - PII detection via pattern matching and contextual heuristics
    - Luhn algorithm for credit card validation (Luhn, 1954)
    - RFC 5322 simplified email validation
    - Multi-layered redaction with severity-weighted risk scoring
    - Arabic/Gulf-specific identifier patterns (IQAMA, Saudi IDs, etc.)
    - Differential anonymization levels (light / medium / strict)

Env toggles:
    MAMOUN_PRIVACY_GUARD_ENABLED — تمكين/تعطيل حارس الخصوصية (الافتراضي: false)
    MAMOUN_PRIVACY_GUARD_DEFAULT_LEVEL — مستوى التخفيض الافتراضي (الافتراضي: medium)
    MAMOUN_PRIVACY_GUARD_LOG_SCANS — تسجيل عمليات المسح (الافتراضي: true)
"""

from __future__ import annotations

import os
import re
import time
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت النظام — System Constants
# ═══════════════════════════════════════════════════════════════════════════════

# إعدادات البيئة — Environment configuration
ENV_ENABLED = os.environ.get("MAMOUN_PRIVACY_GUARD_ENABLED", "false").lower() in (
    "true", "1", "yes", "on",
)
ENV_DEFAULT_LEVEL = os.environ.get(
    "MAMOUN_PRIVACY_GUARD_DEFAULT_LEVEL", "medium"
).lower()
ENV_LOG_SCANS = os.environ.get("MAMOUN_PRIVACY_GUARD_LOG_SCANS", "true").lower() in (
    "true", "1", "yes", "on",
)

# مستويات التخفيض — Anonymization levels
LEVEL_LIGHT = "light"      # تخفيض خفيف — redact only high-severity items
LEVEL_MEDIUM = "medium"    # تخفيض متوسط — redact medium + high severity
LEVEL_STRICT = "strict"    # تخفيض صارم — redact everything

VALID_LEVELS = {LEVEL_LIGHT, LEVEL_MEDIUM, LEVEL_STRICT}

# مستويات الخطورة — Severity levels
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

# أوزان الخطورة لحساب درجة المخاطر — Severity weights for risk score computation
SEVERITY_WEIGHTS: dict[str, float] = {
    SEVERITY_LOW: 0.1,
    SEVERITY_MEDIUM: 0.3,
    SEVERITY_HIGH: 0.6,
    SEVERITY_CRITICAL: 1.0,
}

# عتبات مستوى المخاطر — Risk level thresholds
RISK_LOW_THRESHOLD = 0.2       # أقل من هذا → منخفض
RISK_MEDIUM_THRESHOLD = 0.5    # أقل من هذا → متوسط
RISK_HIGH_THRESHOLD = 0.75     # أعلى من هذا → مرتفع

# عتبة الخطورة للتخفيض حسب المستوى — Severity thresholds per anonymization level
ANON_LEVEL_SEVERITY_THRESHOLD: dict[str, set[str]] = {
    LEVEL_LIGHT: {SEVERITY_HIGH, SEVERITY_CRITICAL},
    LEVEL_MEDIUM: {SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL},
    LEVEL_STRICT: {SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL},
}


# ═══════════════════════════════════════════════════════════════════════════════
# تصنيفات البيانات الحساسة — Sensitive Data Categories
# ═══════════════════════════════════════════════════════════════════════════════

class SensitiveCategory(str, Enum):
    """تصنيفات البيانات الحساسة — Sensitive data categories"""
    PERSONAL_INFO = "personal_info"               # معلومات شخصية
    FINANCIAL = "financial"                        # معلومات مالية
    CREDENTIALS = "credentials"                    # بيانات اعتماد
    MEDICAL = "medical"                            # معلومات طبية
    LOCATION = "location"                          # معلومات الموقع
    RESEARCH = "research"                          # بيانات بحثية
    SYSTEM_ARCHITECTURE = "system_architecture"    # بنية النظام


class SensitiveType(str, Enum):
    """أنواع البيانات الحساسة — Specific sensitive data types"""
    # ─── معلومات شخصية — Personal Info ───
    EMAIL = "email"
    PHONE = "phone"
    PHONE_ARABIC = "phone_arabic"
    NAME = "name"
    ID_NUMBER = "id_number"
    IQAMA = "iqama"
    NATIONAL_ID = "national_id"
    ADDRESS = "address"

    # ─── معلومات مالية — Financial ───
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    CRYPTO_WALLET = "crypto_wallet"
    IBAN = "iban"

    # ─── بيانات اعتماد — Credentials ───
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    JWT = "jwt"
    SECRET = "secret"

    # ─── معلومات طبية — Medical ───
    MEDICAL_CONDITION = "medical_condition"
    PRESCRIPTION = "prescription"
    MEDICAL_RECORD = "medical_record"

    # ─── معلومات الموقع — Location ───
    GPS_COORDINATES = "gps_coordinates"
    SPECIFIC_ADDRESS = "specific_address"

    # ─── بيانات بحثية — Research ───
    UNPUBLISHED_RESEARCH = "unpublished_research"
    PROPRIETARY_DATA = "proprietary_data"

    # ─── بنية النظام — System Architecture ───
    IP_ADDRESS = "ip_address"
    FILE_PATH = "file_path"
    DB_CONNECTION = "db_connection"
    DOCKER_IMAGE = "docker_image"
    URL_WITH_PARAMS = "url_with_params"
    INTERNAL_CONFIG = "internal_config"


# ═══════════════════════════════════════════════════════════════════════════════
# هياكل البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SensitiveItem:
    """
    عنصر حساس — A detected sensitive item within text.
    يمثل قطعة بيانات حساسة تم الكشف عنها مع موقعها وخطورتها.
    """
    type: SensitiveType                              # نوع البيانات الحساسة
    value_preview: str = ""                          # معاينة القيمة (مُقتطعة)
    start: int = 0                                   # موضع البداية في النص
    end: int = 0                                     # موضع النهاية في النص
    severity: str = SEVERITY_MEDIUM                  # مستوى الخطورة
    category: SensitiveCategory = SensitiveCategory.PERSONAL_INFO  # التصنيف

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "type": self.type.value,
            "value_preview": self.value_preview,
            "start": self.start,
            "end": self.end,
            "severity": self.severity,
            "category": self.category.value,
        }


@dataclass
class ScanResult:
    """
    نتيجة المسح — Complete scan result for a data string.
    نتيجة شاملة للمسح تشمل العناصر المكتشفة والنص المنظف ودرجة المخاطر.
    """
    items_found: int = 0                                      # عدد العناصر المكتشفة
    categories_affected: list[str] = field(default_factory=list)  # التصنيفات المتأثرة
    redacted_text: str = ""                                   # النص بعد التنظيف
    anonymization_level: str = LEVEL_MEDIUM                   # مستوى التخفيض
    risk_score: float = 0.0                                   # درجة المخاطر (0-1)
    items: list[SensitiveItem] = field(default_factory=list)   # تفاصيل العناصر

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "items_found": self.items_found,
            "categories_affected": self.categories_affected,
            "redacted_text": self.redacted_text,
            "anonymization_level": self.anonymization_level,
            "risk_score": round(self.risk_score, 4),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class AuditEntry:
    """
    سجل المراجعة — An audit log entry for a scan operation.
    سجل مراجعة لكل عملية مسح لتتبع جميع عمليات الفحص.
    """
    timestamp: float = 0.0                    # وقت العملية (Unix timestamp)
    scan_type: str = "full"                   # نوع المسح (full/category-specific)
    items_found: int = 0                      # عدد العناصر المكتشفة
    risk_level: str = "low"                   # مستوى المخاطر
    action_taken: str = "redacted"            # الإجراء المتخذ (redacted/blocked/passed)
    data_hash: str = ""                       # تجزئة البيانات الممسوحة (SHA-256)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "scan_type": self.scan_type,
            "items_found": self.items_found,
            "risk_level": self.risk_level,
            "action_taken": self.action_taken,
            "data_hash": self.data_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# أنماط الكشف — Detection Patterns
# ═══════════════════════════════════════════════════════════════════════════════

# ─── البريد الإلكتروني — Email (RFC 5322 simplified) ───
PATTERN_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# ─── أرقام الهاتف الدولية — International phone numbers ───
PATTERN_PHONE_INTERNATIONAL = re.compile(
    r"(?:\+|00)\s*\d{1,3}[\s.\-]?\(?\d{1,4}\)?[\s.\-]?\d{1,4}[\s.\-]?\d{1,9}",
)

# ─── أرقام الهاتف السعودية — Saudi phone numbers ───
# الصيغ: +966 5X XXX XXXX أو 05XXXXXXXX
PATTERN_PHONE_SAUDI = re.compile(
    r"(?:\+966|00966)\s*5\d[\s.\-]?\d{3}[\s.\-]?\d{4}"
    r"|"
    r"05\d[\s.\-]?\d{3}[\s.\-]?\d{4}",
)

# ─── أرقام هاتف قطر — Qatar phone numbers ───
# الصيغ: +974 XXXX XXXX
PATTERN_PHONE_QATAR = re.compile(
    r"(?:\+974|00974)\s*\d{4}[\s.\-]?\d{4}",
)

# ─── أرقام هاتف الإمارات — UAE phone numbers ───
# الصيغ: +971 5X XXX XXXX أو 05X XXX XXXX
PATTERN_PHONE_UAE = re.compile(
    r"(?:\+971|00971)\s*5\d[\s.\-]?\d{3}[\s.\-]?\d{3}"
    r"|"
    r"05\d[\s.\-]?\d{3}[\s.\-]?\d{3}",
)

# ─── أرقام الهاتف العامة (أمريكا/أوروبا) — General phone ───
PATTERN_PHONE_GENERAL = re.compile(
    r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}"
)

# ─── الهوية الوطنية / الإقامة السعودية — Saudi National ID / IQAMA ───
# 10 أرقام تبدأ بـ 1 (هوية وطنية) أو 2 (إقامة)
PATTERN_SAUDI_NATIONAL_ID = re.compile(
    r"\b1\d{9}\b",  # يبدأ بـ 1 — starts with 1
)
PATTERN_IQAMA = re.compile(
    r"\b2\d{9}\b",  # يبدأ بـ 2 — starts with 2
)

# ─── أرقام الهوية الخليجية العامة — General Gulf IDs (10 digits) ───
PATTERN_GULF_ID = re.compile(
    r"\b[1-9]\d{9}\b",  # 10 أرقام لا تبدأ بصفر — 10 digits not starting with 0
)

# ─── بطاقات الائتمان — Credit card numbers ───
# أنماط Visa, Mastercard, Amex, Discover مع مسافات أو شرطات
PATTERN_CREDIT_CARD = re.compile(
    r"\b(?:"
    r"4\d{3}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}"   # Visa
    r"|"
    r"5[1-5]\d{2}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}"  # Mastercard
    r"|"
    r"3[47]\d{2}[\s.\-]?\d{6}[\s.\-]?\d{5}"              # Amex
    r"|"
    r"6(?:011|5\d{2})[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}"  # Discover
    r")\b",
)

# ─── رقم الحساب البنكي (IBAN) — Bank account / IBAN ───
PATTERN_IBAN = re.compile(
    r"\b[A-Z]{2}\d{2}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{0,4}\b",
)

# ─── محافظ العملات الرقمية — Crypto wallet addresses ───
PATTERN_CRYPTO_BTC = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b",  # Bitcoin
)
PATTERN_CRYPTO_ETH = re.compile(
    r"\b0x[a-fA-F0-9]{40}\b",                 # Ethereum
)

# ─── مفاتيح API — API keys ───
PATTERN_API_KEY_OPENAI = re.compile(
    r"\bsk-[a-zA-Z0-9]{20,}\b",               # OpenAI sk-*
)
PATTERN_API_KEY_PUBLIC = re.compile(
    r"\bpk_[a-zA-Z0-9_]{20,}\b",              # Public key pk_*
)
PATTERN_API_KEY_GITHUB = re.compile(
    r"\bghp_[a-zA-Z0-9]{36}\b",               # GitHub ghp_*
)
PATTERN_API_KEY_AWS = re.compile(
    r"\bAKIA[A-Z0-9]{16}\b",                  # AWS AKIA*
)
PATTERN_API_KEY_GENERIC = re.compile(
    r"\b(?:api[_\-]?key|apikey)\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?",
    re.IGNORECASE,
)

# ─── كلمات المرور — Passwords ───
PATTERN_PASSWORD = re.compile(
    r"\b(?:password|passwd|pwd|pass)\s*[=:]\s*['\"]?[^\s'\"]{8,}['\"]?",
    re.IGNORECASE,
)

# ─── الأسرار العامة — Generic secrets ───
PATTERN_SECRET = re.compile(
    r"\b(?:secret|client_secret|secret_key|private_key|auth_token|access_token)"
    r"\s*[=:]\s*['\"]?[a-zA-Z0-9_\-/+=]{16,}['\"]?",
    re.IGNORECASE,
)

# ─── رموز JWT — JWT tokens ───
PATTERN_JWT = re.compile(
    r"\beyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\b",
)

# ─── عناوين IP — IP addresses ───
PATTERN_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\b",
)
PATTERN_IPV6 = re.compile(
    r"(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
    r"|"
    r"(?:(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})?::"
    r"(?:(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})?)",
)

# ─── روابط URL مع معلمات — URLs with query parameters ───
PATTERN_URL_WITH_PARAMS = re.compile(
    r"https?://[^\s<>\"]+\?[^\s<>\"]+",
)

# ─── إحداثيات GPS — GPS coordinates ───
PATTERN_GPS = re.compile(
    r"(?:lat(?:itude)?|lon(?:gitude)?)\s*[=:]\s*-?\d{1,3}\.\d+"
    r"|"
    r"-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}"
    r"|"
    r"\b\d{1,2}°\d{1,2}'\d{1,2}\"[NS]\s*\d{1,3}°\d{1,2}'\d{1,2}\"[EW]\b",
    re.IGNORECASE,
)

# ─── مسارات الملفات — File paths ───
PATTERN_FILE_PATH = re.compile(
    r"(?:(?:/home|/etc|/var|/usr|/opt|/tmp|/root|/srv|C:\\|D:\\|\\\\)"
    r"[\\/\w.\-]+[\\/][\w.\-]+)",
)

# ─── سلاسل اتصال قاعدة البيانات — Database connection strings ───
PATTERN_DB_CONNECTION = re.compile(
    r"\b(?:mongodb|postgres|mysql|redis|amqp|ftp|ssh)"
    r"://[a-zA-Z0-9_\-:]+@[a-zA-Z0-9.\-]+(?:\:\d+)?(?:/[a-zA-Z0-9_\-]+)?",
    re.IGNORECASE,
)

# ─── صور Docker — Docker image names/registry URLs ───
PATTERN_DOCKER_IMAGE = re.compile(
    r"\b(?:[a-z0-9.\-]+(?:\:\d+)?/)?[a-z0-9][a-z0-9.\-]*"
    r"(?:/[a-z0-9][a-z0-9.\-]*)*:[a-zA-Z0-9_.\-]+\b",
)

# ─── الأسماء العربية في سياق رسمي — Arabic names in formal context ───
PATTERN_ARABIC_NAME = re.compile(
    r"(?:السيد|السيدة|الأستاذ|الدكتور|د\.|أ\.د\.|المهندس|الشيخ|الفضيلة|السعادة)"
    r"\s+[\u0600-\u06FF\s]{3,30}",
)

# ─── معلومات طبية — Medical information ───
PATTERN_MEDICAL_CONDITION = re.compile(
    r"\b(?:diagnosed\s+with|medical\s+condition|patient\s+(?:has|with)|"
    r"medical\s+record|health\s+record|prescription\s+(?:for|of)|"
    r"مرض|تشخيص|حالة\s+مرضية|سجل\s+طبي|وصفة\s+طبية|مريض\s+(?:بـ|يعاني))\b",
    re.IGNORECASE,
)

# ─── عنوان محدد — Specific address ───
PATTERN_SPECIFIC_ADDRESS = re.compile(
    r"\b\d+\s+[\w\s]{3,40}(?:street|st|avenue|ave|boulevard|blvd|road|rd|lane|ln|drive|dr)"
    r"(?:[\s,]*(?:apt|suite|unit|#)\s*\d+)?"
    r"[\s,]*[\w\s]{2,20}(?:,\s*\w{2}\s+\d{5}(?:-\d{4})?)?"
    r"|"
    r"(?:شارع|حارة|زقاق|طريق|مبنى|عمارة)\s+[\u0600-\u06FF\s\d]{3,30}",
    re.IGNORECASE,
)

# ─── بيانات بحثية — Research data markers ───
PATTERN_UNPUBLISHED_RESEARCH = re.compile(
    r"\b(?:unpublished\s+(?:research|data|findings|results|manuscript)|"
    r"proprietary\s+(?:data|information|algorithm|method)|"
    r"confidential\s+(?:research|study|data)|"
    r"بحث\s+(?:غير\s+)?منشور|بيانات\s+ملكية|بيانات\s+سرية|خوارزمية\s+خاصة)\b",
    re.IGNORECASE,
)

# ─── بنية النظام الداخلية — Internal system architecture ───
PATTERN_SYSTEM_CONFIG = re.compile(
    r"\b(?:internal\s+(?:server|service|endpoint|api|microservice)|"
    r"production\s+(?:database|server|config|credentials)|"
    r"خادم\s+داخلي|قاعدة\s+بيانات\s+الإنتاج|إعدادات\s+الإنتاج|"
    r"بيانات\s+اعتماد\s+الإنتاج)\b",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# كلمات مفتاحية طبية إضافية — Additional medical keywords
# ═══════════════════════════════════════════════════════════════════════════════

MEDICAL_KEYWORDS_EN: list[str] = [
    "blood type", "blood pressure", "cholesterol level", "blood sugar",
    "HIV positive", "hepatitis", "diabetes type", "cancer diagnosis",
    "mental health diagnosis", "psychiatric medication", "antidepressant",
    "chemotherapy", "radiation therapy", "surgical procedure",
    "hospital admission", "emergency room visit", "lab results",
    "medical insurance id", "medicare number", "ssn",
]

MEDICAL_KEYWORDS_AR: list[str] = [
    "فصيلة الدم", "ضغط الدم", "مستوى الكوليسترول", "سكر الدم",
    "مُتقاعد طبياً", "تشخيص سرطان", "علاج كيميائي", "علاج إشعاعي",
    "عملية جراحية", "دخول مستشفى", "طوارئ", "نتائج تحليل",
    "رقم التأمين الطبي", "سجل مرضي",
]

# كلمات مفتاحية للوصفات الطبية — Prescription keywords
PRESCRIPTION_KEYWORDS_EN: list[str] = [
    "prescription", "dosage", "mg daily", "ml daily", "refill",
    "pharmacy", "drug interaction", "side effects of",
]

PRESCRIPTION_KEYWORDS_AR: list[str] = [
    "وصفة طبية", "جرعة", "ملغ يومياً", "مل يومياً", "صيدلية",
    "تداخل دوائي", "آثار جانبية",
]


# ═══════════════════════════════════════════════════════════════════════════════
# فئة حارس الخصوصية — PrivacyGuard Class
# ═══════════════════════════════════════════════════════════════════════════════

class PrivacyGuard:
    """
    حارس الخصوصية — Privacy Guard System for BABSHARQII (Mamoun) v6.0.

    نظام حماية شامل يفحص البيانات الحساسة وينظفها قبل مغادرة النظام.
    يدعم مستويات تخفيض متعددة وأنماط عربية/خليجية محددة.

    Usage:
        guard = PrivacyGuard()
        result = guard.scan_data("Contact me at ahmed@gmail.com or +966 50 123 4567")
        # result.redacted_text → "Contact me at [REDACTED_EMAIL] or [REDACTED_PHONE]"
    """

    def __init__(
        self,
        enabled: bool | None = None,
        default_level: str | None = None,
        log_scans: bool | None = None,
    ):
        """
        تهيئة حارس الخصوصية.

        Args:
            enabled: تمكين/تعطيل — إذا لم يُحدد يُقرأ من البيئة
            default_level: مستوى التخفيض الافتراضي — light/medium/strict
            log_scans: تسجيل عمليات المسح في سجل المراجعة
        """
        self._enabled = enabled if enabled is not None else ENV_ENABLED
        self._default_level = (
            default_level if default_level in VALID_LEVELS else ENV_DEFAULT_LEVEL
        )
        self._log_scans = log_scans if log_scans is not None else ENV_LOG_SCANS

        # سجل المراجعة — audit log
        self._audit_log: list[AuditEntry] = []

        # عداد العمليات — operation counters
        self._total_scans = 0
        self._total_items_detected = 0
        self._total_redactions = 0

        logger.info(
            "حارس الخصوصية: تم التهيئة — Privacy Guard initialized | "
            "enabled=%s, level=%s, log=%s",
            self._enabled,
            self._default_level,
            self._log_scans,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # الواجهة الرئيسية — Public API
    # ══════════════════════════════════════════════════════════════════════════

    def scan_data(
        self,
        data: str,
        level: str | None = None,
        scan_type: str = "full",
    ) -> dict:
        """
        مسح البيانات — Scan data for sensitive information.

        يفحص النص بالكامل للبحث عن معلومات حساسة ويعيد النتيجة
        مع النص المنظف ودرجة المخاطر.

        Args:
            data: النص المراد مسحه — text to scan
            level: مستوى التخفيض — light/medium/strict (الافتراضي: الإعداد العام)
            scan_type: نوع المسح — full/category-specific

        Returns:
            dict — نتيجة المسح الشاملة (ScanResult.to_dict())
        """
        if not self._enabled:
            # الحارس معطل — إرجاع البيانات كما هي — guard disabled, return as-is
            return ScanResult(
                items_found=0,
                redacted_text=data,
                anonymization_level=self._default_level,
                risk_score=0.0,
            ).to_dict()

        if not data or not isinstance(data, str):
            return ScanResult(
                items_found=0,
                redacted_text=data if isinstance(data, str) else "",
                anonymization_level=self._default_level,
                risk_score=0.0,
            ).to_dict()

        anon_level = level if level in VALID_LEVELS else self._default_level

        # ─── جمع كل العناصر الحساسة — collect all sensitive items ───
        all_items: list[SensitiveItem] = []

        if scan_type == "full" or scan_type == "personal":
            all_items.extend(self._detect_personal_info(data))
        if scan_type == "full" or scan_type == "financial":
            all_items.extend(self._detect_financial_info(data))
        if scan_type == "full" or scan_type == "credentials":
            all_items.extend(self._detect_credentials(data))
        if scan_type == "full" or scan_type == "medical":
            all_items.extend(self._detect_medical_info(data))
        if scan_type == "full" or scan_type == "location":
            all_items.extend(self._detect_location_info(data))
        if scan_type == "full" or scan_type == "research":
            all_items.extend(self._detect_research_info(data))
        if scan_type == "full" or scan_type == "system":
            all_items.extend(self._detect_system_architecture(data))

        # ─── إزالة التداخلات — remove overlapping items ───
        all_items = self._remove_overlaps(all_items)

        # ─── حساب درجة المخاطر — compute risk score ───
        risk_score = self._compute_risk_score(all_items)

        # ─── تنظيف النص — redact text ───
        redacted = self._redact(data, all_items, anon_level)

        # ─── التصنيفات المتأثرة — affected categories ───
        categories = sorted(set(
            item.category.value for item in all_items
        ))

        # ─── تحديث العدادات — update counters ───
        self._total_scans += 1
        self._total_items_detected += len(all_items)
        self._total_redactions += sum(
            1 for item in all_items
            if item.severity in ANON_LEVEL_SEVERITY_THRESHOLD.get(anon_level, set())
        )

        # ─── تحديد مستوى المخاطر — determine risk level ───
        risk_level = self._determine_risk_level(risk_score)

        # ─── تحديد الإجراء المتخذ — determine action taken ───
        if risk_score >= RISK_HIGH_THRESHOLD:
            action = "blocked"
        elif risk_score >= RISK_MEDIUM_THRESHOLD:
            action = "redacted"
        else:
            action = "passed"

        # ─── تسجيل المراجعة — audit logging ───
        if self._log_scans:
            data_hash = hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
            entry = AuditEntry(
                timestamp=time.time(),
                scan_type=scan_type,
                items_found=len(all_items),
                risk_level=risk_level,
                action_taken=action,
                data_hash=data_hash,
            )
            self._audit_log.append(entry)

        result = ScanResult(
            items_found=len(all_items),
            categories_affected=categories,
            redacted_text=redacted,
            anonymization_level=anon_level,
            risk_score=risk_score,
            items=all_items,
        )

        if ENV_LOG_SCANS:
            logger.info(
                "حارس الخصوصية: مسح مكتمل — Scan complete | "
                "items=%d, risk=%.2f, level=%s, action=%s",
                len(all_items),
                risk_score,
                anon_level,
                action,
            )

        return result.to_dict()

    def get_status(self) -> dict:
        """
        حالة الحارس — Current privacy guard status.

        Returns:
            dict — حالة النظام الحالية مع إحصائيات
        """
        return {
            "enabled": self._enabled,
            "default_level": self._default_level,
            "log_scans": self._log_scans,
            "total_scans": self._total_scans,
            "total_items_detected": self._total_items_detected,
            "total_redactions": self._total_redactions,
            "audit_log_size": len(self._audit_log),
        }

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """
        سجل المراجعة — Audit trail of all scans.

        Args:
            limit: الحد الأقصى للسجلات المُرجعة (الافتراضي: 50)

        Returns:
            list[dict] — قائمة سجلات المراجعة من الأحدث للأقدم
        """
        entries = self._audit_log[-limit:] if limit > 0 else self._audit_log
        return [entry.to_dict() for entry in reversed(entries)]

    # ══════════════════════════════════════════════════════════════════════════
    # كاشفات المعلومات الحساسة — Sensitive Information Detectors
    # ══════════════════════════════════════════════════════════════════════════

    def _detect_personal_info(self, text: str) -> list[SensitiveItem]:
        """
        كشف المعلومات الشخصية — Detect PII: names, emails, phones, IDs, addresses.

        يبحث عن البريد الإلكتروني، أرقام الهاتف (دولية وعربية)،
        أرقام الهوية والإقامة، والأسماء العربية الرسمية.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — العناصر الحساسة المكتشفة
        """
        items: list[SensitiveItem] = []

        # ─── البريد الإلكتروني — Email ───
        for match in PATTERN_EMAIL.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.EMAIL,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.PERSONAL_INFO,
            ))

        # ─── أرقام الهاتف السعودية — Saudi phone ───
        for match in PATTERN_PHONE_SAUDI.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.PHONE_ARABIC,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.PERSONAL_INFO,
            ))

        # ─── أرقام هاتف قطر — Qatar phone ───
        for match in PATTERN_PHONE_QATAR.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.PHONE_ARABIC,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.PERSONAL_INFO,
            ))

        # ─── أرقام هاتف الإمارات — UAE phone ───
        for match in PATTERN_PHONE_UAE.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.PHONE_ARABIC,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.PERSONAL_INFO,
            ))

        # ─── أرقام هاتف دولية عامة — International phone ───
        for match in PATTERN_PHONE_INTERNATIONAL.finditer(text):
            # تجنب التداخل مع الأرقام العربية المكتشفة سابقاً
            if not self._overlaps_with(match.start(), match.end(), items):
                items.append(SensitiveItem(
                    type=SensitiveType.PHONE,
                    value_preview=self._preview(match.group()),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_HIGH,
                    category=SensitiveCategory.PERSONAL_INFO,
                ))

        # ─── أرقام هاتف عامة (أمريكا/أوروبا) — General phone ───
        for match in PATTERN_PHONE_GENERAL.finditer(text):
            if not self._overlaps_with(match.start(), match.end(), items):
                items.append(SensitiveItem(
                    type=SensitiveType.PHONE,
                    value_preview=self._preview(match.group()),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_MEDIUM,
                    category=SensitiveCategory.PERSONAL_INFO,
                ))

        # ─── الإقامة السعودية (IQAMA) — يبدأ بـ 2 ───
        for match in PATTERN_IQAMA.finditer(text):
            # التحقق من أن السياق يشير لهوية وليس رقم عادي
            if self._is_id_context(text, match.start(), match.end()):
                items.append(SensitiveItem(
                    type=SensitiveType.IQAMA,
                    value_preview=self._preview(match.group()),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_CRITICAL,
                    category=SensitiveCategory.PERSONAL_INFO,
                ))

        # ─── الهوية الوطنية السعودية — يبدأ بـ 1 ───
        for match in PATTERN_SAUDI_NATIONAL_ID.finditer(text):
            if self._is_id_context(text, match.start(), match.end()):
                items.append(SensitiveItem(
                    type=SensitiveType.NATIONAL_ID,
                    value_preview=self._preview(match.group()),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_CRITICAL,
                    category=SensitiveCategory.PERSONAL_INFO,
                ))

        # ─── أرقام هوية خليجية عامة — General Gulf ID ───
        for match in PATTERN_GULF_ID.finditer(text):
            if not self._overlaps_with(match.start(), match.end(), items):
                if self._is_id_context(text, match.start(), match.end()):
                    items.append(SensitiveItem(
                        type=SensitiveType.ID_NUMBER,
                        value_preview=self._preview(match.group()),
                        start=match.start(),
                        end=match.end(),
                        severity=SEVERITY_HIGH,
                        category=SensitiveCategory.PERSONAL_INFO,
                    ))

        # ─── الأسماء العربية في سياق رسمي — Arabic formal names ───
        for match in PATTERN_ARABIC_NAME.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.NAME,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_MEDIUM,
                category=SensitiveCategory.PERSONAL_INFO,
            ))

        # ─── العناوين المحددة — Specific addresses ───
        for match in PATTERN_SPECIFIC_ADDRESS.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.ADDRESS,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_MEDIUM,
                category=SensitiveCategory.PERSONAL_INFO,
            ))

        return items

    def _detect_financial_info(self, text: str) -> list[SensitiveItem]:
        """
        كشف المعلومات المالية — Detect credit cards, bank accounts, crypto wallets.

        يبحث عن أرقام بطاقات الائتمان (مع التحقق بخوارزمية Luhn)،
        حسابات IBAN، ومحافظ العملات الرقمية.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — العناصر المالية الحساسة
        """
        items: list[SensitiveItem] = []

        # ─── بطاقات الائتمان — Credit cards (with Luhn validation) ───
        for match in PATTERN_CREDIT_CARD.finditer(text):
            digits_only = re.sub(r"\D", "", match.group())
            if self._luhn_check(digits_only):
                items.append(SensitiveItem(
                    type=SensitiveType.CREDIT_CARD,
                    value_preview=self._preview(match.group(), max_len=8),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_CRITICAL,
                    category=SensitiveCategory.FINANCIAL,
                ))
            else:
                # رقم مشابه لبطاقة لكنه لا يجتاز Luhn — أقل خطورة
                items.append(SensitiveItem(
                    type=SensitiveType.CREDIT_CARD,
                    value_preview=self._preview(match.group(), max_len=8),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_MEDIUM,
                    category=SensitiveCategory.FINANCIAL,
                ))

        # ─── IBAN ───
        for match in PATTERN_IBAN.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.IBAN,
                value_preview=self._preview(match.group(), max_len=10),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.FINANCIAL,
            ))

        # ─── محافظ بيتكوين — Bitcoin wallets ───
        for match in PATTERN_CRYPTO_BTC.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.CRYPTO_WALLET,
                value_preview=self._preview(match.group(), max_len=12),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.FINANCIAL,
            ))

        # ─── محافظ إيثريوم — Ethereum wallets ───
        for match in PATTERN_CRYPTO_ETH.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.CRYPTO_WALLET,
                value_preview=self._preview(match.group(), max_len=12),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.FINANCIAL,
            ))

        return items

    def _detect_credentials(self, text: str) -> list[SensitiveItem]:
        """
        كشف بيانات الاعتماد — Detect API keys, passwords, tokens, secrets.

        يبحث عن مفاتيح API بصيغها المختلفة (OpenAI, GitHub, AWS, إلخ)،
        كلمات المرور، رموز JWT، والأسرار العامة.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — بيانات الاعتماد المكتشفة
        """
        items: list[SensitiveItem] = []

        # ─── مفاتيح OpenAI — sk-* ───
        for match in PATTERN_API_KEY_OPENAI.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.API_KEY,
                value_preview=self._preview(match.group(), max_len=8),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.CREDENTIALS,
            ))

        # ─── مفاتيح عامة — pk_* ───
        for match in PATTERN_API_KEY_PUBLIC.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.API_KEY,
                value_preview=self._preview(match.group(), max_len=8),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.CREDENTIALS,
            ))

        # ─── مفاتيح GitHub — ghp_* ───
        for match in PATTERN_API_KEY_GITHUB.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.API_KEY,
                value_preview=self._preview(match.group(), max_len=8),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.CREDENTIALS,
            ))

        # ─── مفاتيح AWS — AKIA* ───
        for match in PATTERN_API_KEY_AWS.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.API_KEY,
                value_preview=self._preview(match.group(), max_len=8),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.CREDENTIALS,
            ))

        # ─── مفاتيح API عامة — Generic API keys ───
        for match in PATTERN_API_KEY_GENERIC.finditer(text):
            if not self._overlaps_with(match.start(), match.end(), items):
                items.append(SensitiveItem(
                    type=SensitiveType.API_KEY,
                    value_preview=self._preview(match.group(), max_len=12),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_CRITICAL,
                    category=SensitiveCategory.CREDENTIALS,
                ))

        # ─── كلمات المرور — Passwords ───
        for match in PATTERN_PASSWORD.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.PASSWORD,
                value_preview=self._preview(match.group(), max_len=12),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.CREDENTIALS,
            ))

        # ─── أسرار عامة — Generic secrets ───
        for match in PATTERN_SECRET.finditer(text):
            if not self._overlaps_with(match.start(), match.end(), items):
                items.append(SensitiveItem(
                    type=SensitiveType.SECRET,
                    value_preview=self._preview(match.group(), max_len=12),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_CRITICAL,
                    category=SensitiveCategory.CREDENTIALS,
                ))

        # ─── رموز JWT ───
        for match in PATTERN_JWT.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.JWT,
                value_preview=self._preview(match.group(), max_len=15),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.CREDENTIALS,
            ))

        return items

    def _detect_medical_info(self, text: str) -> list[SensitiveItem]:
        """
        كشف المعلومات الطبية — Detect medical conditions, prescriptions.

        يبحث عن حالات طبية، وصفات، وسجلات طبية باللغتين العربية والإنجليزية.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — المعلومات الطبية الحساسة
        """
        items: list[SensitiveItem] = []

        # ─── أنماط الحالات الطبية — Medical condition patterns ───
        for match in PATTERN_MEDICAL_CONDITION.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.MEDICAL_CONDITION,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.MEDICAL,
            ))

        # ─── كلمات مفتاحية طبية إنجليزية — English medical keywords ───
        text_lower = text.lower()
        for keyword in MEDICAL_KEYWORDS_EN:
            idx = text_lower.find(keyword.lower())
            while idx != -1:
                end_idx = idx + len(keyword)
                if not self._overlaps_with(idx, end_idx, items):
                    items.append(SensitiveItem(
                        type=SensitiveType.MEDICAL_RECORD,
                        value_preview=self._preview(text[idx:end_idx]),
                        start=idx,
                        end=end_idx,
                        severity=SEVERITY_HIGH,
                        category=SensitiveCategory.MEDICAL,
                    ))
                idx = text_lower.find(keyword.lower(), end_idx)

        # ─── كلمات مفتاحية طبية عربية — Arabic medical keywords ───
        for keyword in MEDICAL_KEYWORDS_AR:
            idx = text.find(keyword)
            while idx != -1:
                end_idx = idx + len(keyword)
                if not self._overlaps_with(idx, end_idx, items):
                    items.append(SensitiveItem(
                        type=SensitiveType.MEDICAL_RECORD,
                        value_preview=self._preview(text[idx:end_idx]),
                        start=idx,
                        end=end_idx,
                        severity=SEVERITY_HIGH,
                        category=SensitiveCategory.MEDICAL,
                    ))
                idx = text.find(keyword, end_idx)

        # ─── كلمات مفتاحية للوصفات — Prescription keywords ───
        for keyword in PRESCRIPTION_KEYWORDS_EN:
            idx = text_lower.find(keyword.lower())
            while idx != -1:
                end_idx = idx + len(keyword)
                if not self._overlaps_with(idx, end_idx, items):
                    items.append(SensitiveItem(
                        type=SensitiveType.PRESCRIPTION,
                        value_preview=self._preview(text[idx:end_idx]),
                        start=idx,
                        end=end_idx,
                        severity=SEVERITY_HIGH,
                        category=SensitiveCategory.MEDICAL,
                    ))
                idx = text_lower.find(keyword.lower(), end_idx)

        for keyword in PRESCRIPTION_KEYWORDS_AR:
            idx = text.find(keyword)
            while idx != -1:
                end_idx = idx + len(keyword)
                if not self._overlaps_with(idx, end_idx, items):
                    items.append(SensitiveItem(
                        type=SensitiveType.PRESCRIPTION,
                        value_preview=self._preview(text[idx:end_idx]),
                        start=idx,
                        end=end_idx,
                        severity=SEVERITY_HIGH,
                        category=SensitiveCategory.MEDICAL,
                    ))
                idx = text.find(keyword, end_idx)

        return items

    def _detect_location_info(self, text: str) -> list[SensitiveItem]:
        """
        كشف معلومات الموقع — Detect GPS coordinates, specific addresses.

        يبحث عن إحداثيات GPS وعناوين محددة قد تكشف موقع المستخدم.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — معلومات الموقع الحساسة
        """
        items: list[SensitiveItem] = []

        # ─── إحداثيات GPS ───
        for match in PATTERN_GPS.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.GPS_COORDINATES,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.LOCATION,
            ))

        # ─── عناوين محددة — Specific addresses ───
        for match in PATTERN_SPECIFIC_ADDRESS.finditer(text):
            # تجنب التداخل مع كاشف المعلومات الشخصية
            if not self._overlaps_with(match.start(), match.end(), items):
                items.append(SensitiveItem(
                    type=SensitiveType.SPECIFIC_ADDRESS,
                    value_preview=self._preview(match.group()),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_MEDIUM,
                    category=SensitiveCategory.LOCATION,
                ))

        return items

    def _detect_research_info(self, text: str) -> list[SensitiveItem]:
        """
        كشف البيانات البحثية — Detect unpublished research, proprietary data.

        يبحث عن إشارات لأبحاث غير منشورة أو بيانات خاصة مملوكة.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — البيانات البحثية الحساسة
        """
        items: list[SensitiveItem] = []

        for match in PATTERN_UNPUBLISHED_RESEARCH.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.UNPUBLISHED_RESEARCH,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.RESEARCH,
            ))

        return items

    def _detect_system_architecture(self, text: str) -> list[SensitiveItem]:
        """
        كشف بنية النظام — Detect internal system details, code, configs.

        يبحث عن عناوين IP، مسارات ملفات، سلاسل اتصال قواعد البيانات،
        صور Docker، روابط URL مع معلمات، وإعدادات النظام الداخلية.

        Args:
            text: النص المراد فحصه

        Returns:
            list[SensitiveItem] — تفاصيل بنية النظام الحساسة
        """
        items: list[SensitiveItem] = []

        # ─── عناوين IPv4 ───
        for match in PATTERN_IPV4.finditer(text):
            # استبعاد عناوين خاصة شائعة (127.0.0.1, 0.0.0.0)
            ip = match.group()
            if ip not in ("127.0.0.1", "0.0.0.0", "255.255.255.255"):
                items.append(SensitiveItem(
                    type=SensitiveType.IP_ADDRESS,
                    value_preview=self._preview(ip),
                    start=match.start(),
                    end=match.end(),
                    severity=SEVERITY_MEDIUM,
                    category=SensitiveCategory.SYSTEM_ARCHITECTURE,
                ))

        # ─── عناوين IPv6 ───
        for match in PATTERN_IPV6.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.IP_ADDRESS,
                value_preview=self._preview(match.group(), max_len=20),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_MEDIUM,
                category=SensitiveCategory.SYSTEM_ARCHITECTURE,
            ))

        # ─── روابط URL مع معلمات — URLs with query params ───
        for match in PATTERN_URL_WITH_PARAMS.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.URL_WITH_PARAMS,
                value_preview=self._preview(match.group(), max_len=30),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.SYSTEM_ARCHITECTURE,
            ))

        # ─── مسارات الملفات — File paths ───
        for match in PATTERN_FILE_PATH.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.FILE_PATH,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_MEDIUM,
                category=SensitiveCategory.SYSTEM_ARCHITECTURE,
            ))

        # ─── سلاسل اتصال قواعد البيانات — DB connection strings ───
        for match in PATTERN_DB_CONNECTION.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.DB_CONNECTION,
                value_preview=self._preview(match.group(), max_len=15),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_CRITICAL,
                category=SensitiveCategory.SYSTEM_ARCHITECTURE,
            ))

        # ─── صور Docker — Docker images ───
        for match in PATTERN_DOCKER_IMAGE.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.DOCKER_IMAGE,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_LOW,
                category=SensitiveCategory.SYSTEM_ARCHITECTURE,
            ))

        # ─── إعدادات النظام الداخلية — Internal system config ───
        for match in PATTERN_SYSTEM_CONFIG.finditer(text):
            items.append(SensitiveItem(
                type=SensitiveType.INTERNAL_CONFIG,
                value_preview=self._preview(match.group()),
                start=match.start(),
                end=match.end(),
                severity=SEVERITY_HIGH,
                category=SensitiveCategory.SYSTEM_ARCHITECTURE,
            ))

        return items

    # ══════════════════════════════════════════════════════════════════════════
    # التنظيف والتخفيض — Redaction & Anonymization
    # ══════════════════════════════════════════════════════════════════════════

    def _redact(
        self,
        text: str,
        items: list[SensitiveItem],
        level: str = LEVEL_MEDIUM,
    ) -> str:
        """
        تنظيف النص — Replace sensitive items with [REDACTED_TYPE].

        يستبدل كل عنصر حساس بعلامة تنظيف تحتوي على نوع البيانات.
        يراعي مستوى التخفيض: لا ينظف العناصر ذات الخطورة المنخفضة
        في المستوى الخفيف.

        Args:
            text: النص الأصلي
            items: قائمة العناصر الحساسة
            level: مستوى التخفيض (light/medium/strict)

        Returns:
            str — النص بعد التنظيف
        """
        if not items:
            return text

        # تحديد العناصر التي يجب تنظيفها حسب المستوى — filter by level
        severity_threshold = ANON_LEVEL_SEVERITY_THRESHOLD.get(
            level, ANON_LEVEL_SEVERITY_THRESHOLD[LEVEL_MEDIUM]
        )

        items_to_redact = [
            item for item in items
            if item.severity in severity_threshold
        ]

        if not items_to_redact:
            return text

        # ترتيب عكسي للتنظيف من النهاية — sort reverse to preserve indices
        items_to_redact.sort(key=lambda x: x.start, reverse=True)

        result = text
        for item in items_to_redact:
            # علامة التنظيف — redaction marker
            marker = f"[REDACTED_{item.type.value.upper()}]"
            result = result[:item.start] + marker + result[item.end:]

        return result

    def _anonymize(self, text: str, level: str = LEVEL_MEDIUM) -> str:
        """
        التخفيض — Different anonymization levels.

        مستويات التخفيض:
        - light: تنقيح العناصر عالية الخطورة فقط مع الإبقاء على السياق
        - medium: تنقيح العناصر المتوسطة والعالية مع تعميم السياق
        - strict: تنقيح كل شيء مع إزالة السياق المحيط

        Args:
            text: النص الأصلي
            level: مستوى التخفيض

        Returns:
            str — النص بعد التخفيض
        """
        if not text:
            return text

        # كشف جميع العناصر — detect all items
        all_items: list[SensitiveItem] = []
        all_items.extend(self._detect_personal_info(text))
        all_items.extend(self._detect_financial_info(text))
        all_items.extend(self._detect_credentials(text))
        all_items.extend(self._detect_medical_info(text))
        all_items.extend(self._detect_location_info(text))
        all_items.extend(self._detect_research_info(text))
        all_items.extend(self._detect_system_architecture(text))

        all_items = self._remove_overlaps(all_items)

        # ─── المستوى الخفيف — Light level ───
        if level == LEVEL_LIGHT:
            return self._redact(text, all_items, LEVEL_LIGHT)

        # ─── المستوى المتوسط — Medium level ───
        if level == LEVEL_MEDIUM:
            redacted = self._redact(text, all_items, LEVEL_MEDIUM)
            # إزالة السياق المباشر حول العناصر المنظفة — strip surrounding context
            # مثلاً "email: [REDACTED_EMAIL]" → "[REDACTED_EMAIL]"
            redacted = re.sub(
                r"(?:email|e-mail|بريد)\s*[:：]\s*\[REDACTED",
                "[REDACTED",
                redacted,
                flags=re.IGNORECASE,
            )
            redacted = re.sub(
                r"(?:phone|tel|هاتف|رقم)\s*[:：]\s*\[REDACTED",
                "[REDACTED",
                redacted,
                flags=re.IGNORECASE,
            )
            return redacted

        # ─── المستوى الصارم — Strict level ───
        if level == LEVEL_STRICT:
            redacted = self._redact(text, all_items, LEVEL_STRICT)
            # إزالة جميع السياقات المحيطة — strip all surrounding context
            for prefix_pattern in [
                r"(?:email|e-mail|بريد)\s*[:：]\s*",
                r"(?:phone|tel|هاتف|رقم)\s*[:：]\s*",
                r"(?:address|عنوان)\s*[:：]\s*",
                r"(?:name|اسم|الاسم)\s*[:：]\s*",
                r"(?:id|رقم|هوية)\s*[:：]\s*",
                r"(?:password|كلمة\s+مرور|سر)\s*[:：]\s*",
                r"(?:key|مفتاح)\s*[:：]\s*",
                r"(?:token|رمز)\s*[:：]\s*",
                r"(?:api|واجهة)\s*[:：]\s*",
            ]:
                redacted = re.sub(
                    prefix_pattern + r"(?=\[REDACTED)",
                    "",
                    redacted,
                    flags=re.IGNORECASE,
                )
            # إزالة الجمل التي تحتوي على بيانات حساسة كاملة — remove full sentences
            redacted = re.sub(
                r"[^.!?؟\n]*\[REDACTED_[A-Z_]+\][^.!?؟\n]*[.!?؟]?",
                "[REDACTED]",
                redacted,
            )
            return redacted

        return text

    # ══════════════════════════════════════════════════════════════════════════
    # أدوات مساعدة — Utility Methods
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _preview(value: str, max_len: int = 6) -> str:
        """
        معاينة مقتطعة — Create a truncated preview of a sensitive value.

        يعرض أول حرفين فقط متبوعين بنقاط للإشارة إلى الطول.

        Args:
            value: القيمة الأصلية
            max_len: الحد الأقصى للعرض

        Returns:
            str — معاينة مقتطعة
        """
        if not value:
            return ""
        if len(value) <= max_len:
            return value[:2] + "***" if len(value) > 2 else "***"
        return value[:2] + "..." + value[-2:]

    @staticmethod
    def _luhn_check(number: str) -> bool:
        """
        التحقق بخوارزمية Luhn — Validate credit card number using Luhn algorithm.

        خوارزمية Luhn (1954) للتحقق من صحة أرقام بطاقات الائتمان.

        Args:
            number: سلسلة الأرقام (بدون مسافات أو شرطات)

        Returns:
            bool — هل الرقم صالح حسب Luhn؟
        """
        if not number or not number.isdigit():
            return False

        digits = [int(d) for d in number]
        checksum = 0
        reverse_digits = digits[::-1]

        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    @staticmethod
    def _is_id_context(text: str, start: int, end: int) -> bool:
        """
        هل السياق يشير لهوية؟ — Does the surrounding context indicate an ID number?

        يتحقق من وجود كلمات مفتاحية حول الرقم تدل على أنه رقم هوية
        وليس رقماً عادياً مثل رقم طلب أو كمية.

        Args:
            text: النص الكامل
            start: موضع بداية الرقم
            end: موضع نهاية الرقم

        Returns:
            bool — هل السياق يشير لرقم هوية؟
        """
        # منطقة السياق — context window
        ctx_start = max(0, start - 40)
        ctx_end = min(len(text), end + 40)
        context = text[ctx_start:ctx_end].lower()

        id_keywords = [
            # إنجليزي — English
            "id", "identity", "national", "iqama", "residence", "permit",
            "identification", "citizen", "passport", "number",
            # عربي — Arabic
            "هوية", "رقم", "إقامة", "مواطن", "جواز", "بطاقة",
            "تعريف", "سكان", "مقيم",
        ]

        return any(kw in context for kw in id_keywords)

    @staticmethod
    def _overlaps_with(
        start: int,
        end: int,
        existing_items: list[SensitiveItem],
    ) -> bool:
        """
        هل يتداخل النطاق مع عنصر موجود؟ — Does range overlap with existing items?

        Args:
            start: موضع البداية
            end: موضع النهاية
            existing_items: العناصر الموجودة

        Returns:
            bool — هل يوجد تداخل؟
        """
        for item in existing_items:
            if start < item.end and end > item.start:
                return True
        return False

    @staticmethod
    def _remove_overlaps(items: list[SensitiveItem]) -> list[SensitiveItem]:
        """
        إزالة التداخلات — Remove overlapping items, keeping higher-severity ones.

        عندما يكتشف عدة أنماط نفس المنطقة من النص، يبقي الأعلى خطورة.

        Args:
            items: قائمة العناصر مع التداخلات المحتملة

        Returns:
            list[SensitiveItem] — قائمة بدون تداخلات
        """
        if not items:
            return []

        # ترتيب حسب الخطورة (الأعلى أولاً) ثم حسب الطول (الأطول أولاً)
        severity_order = {
            SEVERITY_CRITICAL: 0,
            SEVERITY_HIGH: 1,
            SEVERITY_MEDIUM: 2,
            SEVERITY_LOW: 3,
        }
        sorted_items = sorted(
            items,
            key=lambda x: (
                severity_order.get(x.severity, 2),
                -(x.end - x.start),
            ),
        )

        result: list[SensitiveItem] = []
        for item in sorted_items:
            overlaps = False
            for existing in result:
                if item.start < existing.end and item.end > existing.start:
                    overlaps = True
                    break
            if not overlaps:
                result.append(item)

        # إعادة ترتيب حسب الموقع — sort by position
        result.sort(key=lambda x: x.start)
        return result

    @staticmethod
    def _compute_risk_score(items: list[SensitiveItem]) -> float:
        """
        حساب درجة المخاطر — Compute risk score based on detected items.

        درجة المخاطر تعتمد على عدد العناصر وخطورة كل عنصر.
        الصيغة: sum(severity_weight) / max_possible_score

        Args:
            items: قائمة العناصر الحساسة

        Returns:
            float — درجة المخاطر (0.0 - 1.0)
        """
        if not items:
            return 0.0

        total_weight = sum(
            SEVERITY_WEIGHTS.get(item.severity, 0.1) for item in items
        )

        # عدد العناصر يزيد المخاطر لكن مع تقليص تدريجي — diminishing returns
        count_factor = 1.0 + 0.1 * min(len(items), 20)

        raw_score = total_weight * count_factor / len(items)

        # تطبيع بين 0 و 1 — normalize to 0-1
        # أقصى وزن ممكن لعنصر واحد هو 1.0 (CRITICAL) مع count_factor أقصى 3.0
        return min(1.0, raw_score / 2.0)

    @staticmethod
    def _determine_risk_level(score: float) -> str:
        """
        تحديد مستوى المخاطر — Determine risk level from score.

        Args:
            score: درجة المخاطر (0.0 - 1.0)

        Returns:
            str — مستوى المخاطر (low/medium/high/critical)
        """
        if score >= RISK_HIGH_THRESHOLD:
            return SEVERITY_CRITICAL
        elif score >= RISK_MEDIUM_THRESHOLD:
            return SEVERITY_HIGH
        elif score >= RISK_LOW_THRESHOLD:
            return SEVERITY_MEDIUM
        else:
            return SEVERITY_LOW


# ═══════════════════════════════════════════════════════════════════════════════
# مثال مُصدَّر — Exported singleton instance
# ═══════════════════════════════════════════════════════════════════════════════

# مثيل افتراضي يُستخدم مباشرة بدون تهيئة — default instance for convenience
default_privacy_guard = PrivacyGuard()


# ═══════════════════════════════════════════════════════════════════════════════
# واجهة مختصرة — Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════════

def scan_data(data: str, level: str | None = None) -> dict:
    """
    مسح البيانات — Quick scan using the default privacy guard instance.

    Args:
        data: النص المراد مسحه
        level: مستوى التخفيض (اختياري)

    Returns:
        dict — نتيجة المسح
    """
    return default_privacy_guard.scan_data(data, level=level)


def get_status() -> dict:
    """حالة الحارس الافتراضي — Status of default guard instance."""
    return default_privacy_guard.get_status()


def get_audit_log(limit: int = 50) -> list[dict]:
    """سجل المراجعة — Audit log from default guard instance."""
    return default_privacy_guard.get_audit_log(limit=limit)
