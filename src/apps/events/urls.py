from django.urls import path

from events import views

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    path('novo/', views.EventCreateView.as_view(), name='event_create'),
    path('<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
]
