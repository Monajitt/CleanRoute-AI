from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.db.utils import OperationalError


class HealthCheckView(APIView):
    """
    Health check endpoint verifying application runtime and live database connectivity.
    GET /api/health/
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        db_status = "disconnected"
        try:
            connection.ensure_connection()
            db_status = "connected"
            http_status = status.HTTP_200_OK
            response_data = {
                "success": True,
                "status": "success",
                "message": "CleanRoute AI backend is running",
                "database": db_status
            }
        except Exception:
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            response_data = {
                "success": False,
                "status": "error",
                "message": "CleanRoute AI backend is running but database is unreachable",
                "database": db_status
            }

        return Response(response_data, status=http_status)
