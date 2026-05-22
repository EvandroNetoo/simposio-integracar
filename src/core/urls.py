from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path(
        '',
        lambda r: (
            redirect('event_list')
            if r.user.is_authenticated
            else redirect('signin')
        ),
    ),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('events.urls')),
    path('', include('papers.urls')),
    path('', include('reviews.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
