from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.static import serve

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

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
else:
    urlpatterns += [
        re_path(
            rf'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
