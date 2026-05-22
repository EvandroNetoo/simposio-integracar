from django.contrib import admin
from django.db.models import Count

from reviews.models import Review, ReviewAssignment, Reviewer


class ReviewInline(admin.StackedInline):
    model = Review
    extra = 0
    fields = (
        'score',
        'recommendation',
        'comments_to_author',
        'internal_comments',
        'submitted_at',
        'updated_at',
    )
    readonly_fields = ('submitted_at', 'updated_at')


@admin.register(Reviewer)
class ReviewerAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'eixos_tematicos_count')
    list_filter = ('event', 'event__year')
    search_fields = (
        'user__email',
        'user__first_name',
        'user__surname',
        'event__name',
        'event__edition',
    )
    autocomplete_fields = ('event', 'user', 'eixos_tematicos')
    list_select_related = ('event', 'user')
    ordering = ('event__year', 'event__name', 'user__email')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            eixos_tematicos_total=Count('eixos_tematicos')
        )

    @admin.display(ordering='eixos_tematicos_total', description='Eixos')
    def eixos_tematicos_count(self, obj):
        return obj.eixos_tematicos_total


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'paper',
        'reviewer',
        'event',
        'assigned_at',
        'completed_at',
    )
    list_filter = ('reviewer__event', 'assigned_at', 'completed_at')
    search_fields = (
        'paper__title',
        'paper__user__email',
        'reviewer__user__email',
        'reviewer__event__name',
        'reviewer__event__edition',
    )
    autocomplete_fields = ('reviewer', 'paper')
    list_select_related = (
        'reviewer',
        'paper',
        'reviewer__event',
        'reviewer__user',
        'paper__user',
    )
    date_hierarchy = 'assigned_at'
    ordering = ('-assigned_at',)
    inlines = [ReviewInline]

    @admin.display(ordering='reviewer__event__name', description='Event')
    def event(self, obj):
        return obj.reviewer.event


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'paper',
        'reviewer',
        'recommendation',
        'score',
        'submitted_at',
        'updated_at',
    )
    list_filter = (
        'recommendation',
        'submitted_at',
        'updated_at',
        'assignment__reviewer__event',
    )
    search_fields = (
        'assignment__paper__title',
        'assignment__paper__user__email',
        'assignment__reviewer__user__email',
        'assignment__reviewer__event__name',
        'assignment__reviewer__event__edition',
    )
    autocomplete_fields = ('assignment',)
    list_select_related = (
        'assignment',
        'assignment__paper',
        'assignment__reviewer',
        'assignment__reviewer__user',
        'assignment__reviewer__event',
    )
    date_hierarchy = 'submitted_at'
    ordering = ('-submitted_at',)
    readonly_fields = ('submitted_at', 'updated_at')

    @admin.display(ordering='assignment__paper__title', description='Paper')
    def paper(self, obj):
        return obj.assignment.paper

    @admin.display(
        ordering='assignment__reviewer__user__email', description='Reviewer'
    )
    def reviewer(self, obj):
        return obj.assignment.reviewer
