from django.contrib import admin

from reviews.models import (
    CommitteeMember,
    FinalDecision,
    Review,
    ReviewAssignment,
    Reviewer,
)


@admin.register(CommitteeMember)
class CommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'is_manager', 'is_decider')
    list_filter = ('event', 'is_manager', 'is_decider')
    autocomplete_fields = ('user', 'event')


@admin.register(Reviewer)
class ReviewerAdmin(admin.ModelAdmin):
    list_display = ('user', 'event')
    list_filter = ('event',)
    autocomplete_fields = ('event', 'user', 'eixos_tematicos')
    search_fields = ('user__email', 'event__name')


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('paper', 'reviewer', 'assigned_at', 'completed_at')
    list_filter = ('paper__event', 'completed_at')
    autocomplete_fields = ('reviewer', 'paper')
    search_fields = ('paper__title', 'reviewer__user__email')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'assignment',
        'recommendation',
        'updated_at',
    )
    list_filter = ('recommendation', 'assignment__paper__event')
    autocomplete_fields = ('assignment',)
    readonly_fields = ('submitted_at', 'updated_at')


@admin.register(FinalDecision)
class FinalDecisionAdmin(admin.ModelAdmin):
    list_display = ('paper', 'result', 'decided_by', 'published_at')
    list_filter = ('result', 'paper__event')
    autocomplete_fields = ('paper', 'decided_by')
    readonly_fields = ('published_at',)
