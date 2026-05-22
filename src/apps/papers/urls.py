from django.urls import path

from papers import views

urlpatterns = [
    path(
        'eventos/<int:event_pk>/trabalhos/novo',
        views.PaperCreateView.as_view(),
        name='paper_create',
    ),
    path(
        'eventos/<int:event_pk>/trabalhos/<int:pk>/',
        views.PaperDetailView.as_view(),
        name='paper_detail',
    ),
    path(
        'eventos/<int:event_pk>/trabalhos/<int:pk>/editar',
        views.PaperUpdateView.as_view(),
        name='paper_change',
    ),
]
