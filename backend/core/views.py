from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from django.db import connection
from .negotiation import IgnoreClientContentNegotiation


class HealthCheckView(APIView):
    """
    Health check endpoint verifying application runtime and live database connectivity.
    GET /api/health/
    """
    authentication_classes = []
    permission_classes = []
    renderer_classes = [JSONRenderer]
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request):
        db_status = "disconnected"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
            db_status = "connected"
            http_status = status.HTTP_200_OK
            response_data = {
                "status": "ok",
                "success": True,
                "message": "CleanRoute AI backend is running",
                "database": db_status
            }
        except Exception as db_err:
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            response_data = {
                "status": "error",
                "success": False,
                "message": "CleanRoute AI backend is running but database is unreachable",
                "database": db_status,
                "details": str(db_err)
            }

        return Response(response_data, status=http_status)

