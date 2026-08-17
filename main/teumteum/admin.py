from django.contrib import admin

from .models import WellnessArticleSource, ActivityModuleTemplate


@admin.register(WellnessArticleSource)
class WellnessArticleSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source", "topics", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "content", "source")


@admin.register(ActivityModuleTemplate)
class ActivityModuleTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "content_type", "estimated_minutes", "is_active")
    list_filter = ("content_type", "is_active")
    search_fields = ("title",)
