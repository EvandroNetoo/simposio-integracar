from django.contrib import admin
from reviews.models import Reviewer

from events.models import EixoTematico, Event


class EixoTematicoInline(admin.TabularInline):
    model = EixoTematico
    extra = 0


class ReviewerInline(admin.TabularInline):
    model = Reviewer
    extra = 0
    autocomplete_fields = ('user', 'eixos_tematicos')
    show_change_link = True


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'edition',
        'year',
        'organizing_institution',
        'submission_period_start',
        'submission_period_end',
        'results_publication_date',
        'blind_review',
        'minimum_reviewers',
    )
    list_filter = ('year', 'blind_review', 'organizing_institution')
    search_fields = (
        'name',
        'edition',
        'organizing_institution',
        'contact_email',
    )
    date_hierarchy = 'submission_period_start'
    ordering = ('-year', 'name', 'edition')
    autocomplete_fields = ('owner',)
    list_select_related = ('owner',)
    inlines = [EixoTematicoInline, ReviewerInline]
    fieldsets = (
        (
            'Event info',
            {
                'fields': (
                    'name',
                    'edition',
                    'year',
                    'organizing_institution',
                    'owner',
                )
            },
        ),
        (
            'Submission period',
            {
                'fields': (
                    ('submission_period_start', 'submission_period_end'),
                )
            },
        ),
        (
            'Evaluation period',
            {
                'fields': (
                    ('evaluation_period_start', 'evaluation_period_end'),
                )
            },
        ),
        (
            'Results',
            {'fields': ('results_publication_date',)},
        ),
        (
            'Contact',
            {'fields': ('contact_email',)},
        ),
        (
            'Rules and review',
            {
                'fields': (
                    'submission_rules',
                    'blind_review',
                    'minimum_reviewers',
                )
            },
        ),
    )


@admin.register(EixoTematico)
class EixoTematicoAdmin(admin.ModelAdmin):
    list_display = ('name', 'event')
    list_filter = ('event',)
    search_fields = ('name', 'event__name', 'event__edition')
    autocomplete_fields = ('event',)
    list_select_related = ('event',)
    ordering = ('event__year', 'event__name', 'name')
