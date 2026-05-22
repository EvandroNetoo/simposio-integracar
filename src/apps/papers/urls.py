from django.urls import path

from papers import views

urlpatterns = [
    path(
        'trabalhos/',
        views.PaperListView.as_view(),
        name='paper_list',
    ),
    path(
        'eventos/<int:event_pk>/trabalhos/novo',
        views.PaperCreateView.as_view(),
        name='paper_create',
    ),
    path(
        'trabalhos/<int:pk>/',
        views.PaperDetailView.as_view(),
        name='paper_detail',
    ),
    path(
        'trabalhos/<int:pk>/editar',
        views.PaperUpdateView.as_view(),
        name='paper_change',
    ),
    path(
        'trabalhos/<int:pk>/submissoes/nova',
        views.SubmissionCreateView.as_view(),
        name='submission_create',
    ),
]
