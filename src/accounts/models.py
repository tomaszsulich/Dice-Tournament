import re

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

# English status terms are covered as the initial baseline.
# User-facing terms in other languages may be added as needed.
FORBIDDEN_NICKNAME_PATTERNS = (
    r"\bzwyci[eę]zca\b",
    r"\bzwyci[eę]zczyni\b",
    r"\bwygran(?:y|a)\b",
    r"\bprzegran(?:y|a)\b",
    r"\bmistrz\b",
    r"\bmistrzyni\b",
    r"\bchampion\b",
    r"\bwinner\b",
    r"\bloser\b",
    r"\b(?:1|2|3)\.?\s*miejsce\b",
    r"\bpierwsze\s+miejsce\b",
    r"\bdrugie\s+miejsce\b",
    r"\btrzecie\s+miejsce\b",
    r"\btop\s*\d+\b",
    r"\bnajlepsz(?:y|a)\s+gracz\b",
    r"\bnajgorsz(?:y|a)\s+gracz\b",
)


def validate_nickname(value: str) -> None:
    normalized = " ".join(value.casefold().split())

    if any(re.search(pattern, normalized) for pattern in FORBIDDEN_NICKNAME_PATTERNS):
        raise ValidationError(
            "Nickname cannot suggest a tournament result, position or status."
        )


class User(AbstractUser):
    created_at = models.DateTimeField(auto_now_add=True)


class PlayerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="player_profile",
    )

    display_name = models.CharField(max_length=150)

    nickname = models.CharField(
        max_length=50,
        blank=True,
        validators=[validate_nickname],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nickname or self.display_name
