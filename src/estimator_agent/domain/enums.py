from enum import StrEnum


class Language(StrEnum):
    EN = "en"
    TE = "te"
    HI = "hi"


class InputMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class Intent(StrEnum):
    ESTIMATE = "estimate"
    QUESTION = "question"
    MODIFY = "modify"
    CONTACT = "contact"
    CHIT_CHAT = "chit_chat"
    OFF_TOPIC = "off_topic"


class ProjectType(StrEnum):
    NEW_HOUSE = "new_house"
    COMMERCIAL = "commercial"
    RENOVATION = "renovation"
    INTERIOR = "interior"
    COMPOUND_WALL = "compound_wall"


class QualityTier(StrEnum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class Extra(StrEnum):
    LIFT = "lift"
    CELLAR_PARKING = "cellar_parking"
    SOLAR = "solar"
    SUMP = "sump"
    COMPOUND_WALL = "compound_wall"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"


class ContactChannel(StrEnum):
    CALL = "call"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    VISIT = "visit"
