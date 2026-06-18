from django.contrib import admin

from reviews.models import (
    CommitteeMember,
    CriterionScore,
    FinalDecision,
    Review,
    ReviewAssignment,
    ReviewCriterion,
    Reviewer,
    ReviewInstrument,
    ReviewRound,
)


class ReviewCriterionInline(admin.TabularInline):
    model = ReviewCriterion
    extra = 0


class CriterionScoreInline(admin.TabularInline):
    model = CriterionScore
    extra = 0


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


@admin.register(ReviewInstrument)
class ReviewInstrumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'version', 'created_at')
    list_filter = ('event',)
    autocomplete_fields = ('event', 'created_by')
    inlines = (ReviewCriterionInline,)
    search_fields = ('name', 'event__name')


@admin.register(ReviewRound)
class ReviewRoundAdmin(admin.ModelAdmin):
    list_display = ('paper', 'number', 'status', 'starts_at', 'ends_at')
    list_filter = ('status', 'paper__event')
    autocomplete_fields = ('paper', 'submission', 'instrument', 'created_by')
    search_fields = ('paper__title', 'paper__event__name')


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('round', 'reviewer', 'assigned_at', 'completed_at')
    list_filter = ('round__paper__event', 'completed_at')
    autocomplete_fields = ('reviewer', 'round')
    search_fields = ('round__paper__title', 'reviewer__user__email')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'assignment',
        'recommendation',
        'weighted_score',
        'updated_at',
    )
    list_filter = ('recommendation', 'assignment__round__paper__event')
    autocomplete_fields = ('assignment',)
    readonly_fields = ('weighted_score', 'submitted_at', 'updated_at')
    inlines = (CriterionScoreInline,)


@admin.register(FinalDecision)
class FinalDecisionAdmin(admin.ModelAdmin):
    list_display = ('round', 'result', 'decided_by', 'published_at')
    list_filter = ('result', 'round__paper__event')
    autocomplete_fields = ('round', 'decided_by')
    readonly_fields = ('published_at',)
