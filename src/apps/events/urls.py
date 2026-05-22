from django.urls import path

from events import views

urlpatterns = [
    path('eventos/', views.EventListView.as_view(), name='event_list'),
    path(
        'eventos/novo/', views.EventCreateView.as_view(), name='event_create'
    ),
    path(
        'eventos/<int:pk>/',
        views.EventDetailView.as_view(),
        name='event_detail',
    ),
]
