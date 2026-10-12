from django.urls import include, path

urlpatterns = [
    path("", include("tickets.urls")),
]

handler404 = "config.views.not_found"
handler500 = "config.views.server_error"
