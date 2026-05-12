from enum import Enum


CONFIDENCE_THRESHOLD = 0.7

CLASS_NAMES: list[str] = [
    "letter",               # 0
    "form",                 # 1
    "email",                # 2
    "handwritten",          # 3
    "advertisement",        # 4
    "scientific_report",    # 5
    "scientific_publication", # 6
    "specification",        # 7
    "file_folder",          # 8
    "news_article",         # 9
    "budget",               # 10
    "invoice",              # 11
    "presentation",         # 12
    "questionnaire",        # 13
    "resume",               # 14
    "memo",                 # 15
]


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class UserRole(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"
