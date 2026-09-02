from django.db import models


class TournamentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REGISTRATION = "registration", "Registration"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"


class RegistrationMode(models.TextChoices):
    ORGANIZER_ONLY = "organizer_only", "Organizer only"
    OPEN = "open", "Open"


class EventMode(models.TextChoices):
    IN_PERSON = "in_person", "In person"
    REMOTE = "remote", "Remote"


class DecisionTimeLimit(models.IntegerChoices):
    UNLIMITED = 0, "Unlimited"
    SECONDS_30 = 30, "30 seconds"
    SECONDS_60 = 60, "60 seconds"
    SECONDS_90 = 90, "90 seconds"
