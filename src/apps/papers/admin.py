from django.contrib import admin

from papers.models import Coauthor, Paper, Submission


class CoauthorInline(admin.TabularInline):
    model = Coauthor
    extra = 0
    autocomplete_fields = ('user',)
    fields = (
        'authorship_order',
        'user',
        'name',
        'email',
        'institution',
        'affiliation_type',
    )
    ordering = ('authorship_order', 'name')


class SubmissionInline(admin.StackedInline):
    model = Submission
    extra = 0
    fields = ('file', 'observations', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = (
        'title',
        'user__email',
        'user__first_name',
        'user__surname',
    )
    autocomplete_fields = ('user',)
    list_select_related = ('user',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    inlines = [CoauthorInline, SubmissionInline]
    fieldsets = (
        (
            'Paper info',
            {
                'fields': (
                    'title',
                    'abstract',
                    'user',
                )
            },
        ),
        (
            'Timestamps',
            {'fields': ('created_at',)},
        ),
    )


@admin.register(Coauthor)
class CoauthorAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'paper',
        'user',
        'affiliation_type',
        'authorship_order',
    )
    list_filter = ('affiliation_type',)
    search_fields = (
        'name',
        'email',
        'institution',
        'paper__title',
        'user__email',
        'user__first_name',
        'user__surname',
    )
    autocomplete_fields = ('paper', 'user')
    list_select_related = ('paper', 'user')
    ordering = ('paper', 'authorship_order', 'name')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('paper', 'file', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('paper__title', 'paper__user__email')
    autocomplete_fields = ('paper',)
    list_select_related = ('paper', 'paper__user')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
