from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import PlayerProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "nickname", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "display_name",
        "nickname",
    )
