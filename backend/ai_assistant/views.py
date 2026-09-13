import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ChatMessageSerializer, ChatResponseSerializer
from .services import AIAssistantService, RESPONSIBLE_AI_DISCLAIMER

logger = logging.getLogger(__name__)


class ChatAPIView(APIView):
    """
    CleanRoute AI Assistant Conversational Endpoint.
    Integrates Local RAG knowledge base retrieval with active route journey context.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Invalid chat request.",
                        "details": serializer.errors
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user_message = serializer.validated_data["message"]
        route_context = serializer.validated_data.get("route_context")

        try:
            response_payload = AIAssistantService.generate_grounded_response(
                user_message=user_message,
                route_context=route_context
            )

            out_serializer = ChatResponseSerializer(data={"success": True, "data": response_payload})
            if out_serializer.is_valid():
                return Response(out_serializer.data, status=status.HTTP_200_OK)

            return Response(
                {"success": True, "data": response_payload},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Chat processing error: {e}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "An error occurred while formulating the assistant response.",
                        "details": str(e)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """
        Returns assistant service metadata and suggested prompts.
        """
        return Response(
            {
                "success": True,
                "data": {
                    "service": "CleanRoute AI Assistant (Local RAG)",
                    "status": "ready",
                    "suggested_questions": [
                        "Why was this route recommended?",
                        "What does PM2.5 mean?",
                        "Why is cycling considered sustainable?",
                        "How does pollution affect the route recommendation?",
                        "Why choose Health First?"
                    ],
                    "disclaimer": RESPONSIBLE_AI_DISCLAIMER
                }
            },
            status=status.HTTP_200_OK
        )
