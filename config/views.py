"""JSON error handlers so unmatched API routes and crashes keep the API's error shape."""

from django.http import JsonResponse


def not_found(request, exception=None):
    return JsonResponse({"error": {"code": "not_found", "message": "Not found"}}, status=404)


def server_error(request):
    return JsonResponse(
        {"error": {"code": "internal_error", "message": "Something went wrong"}}, status=500
    )
