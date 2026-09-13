from rest_framework import serializers


class ChatSourceSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    source = serializers.CharField()
    topic = serializers.CharField(required=False)


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={"blank": "Message query cannot be empty.", "required": "A message string is required."}
    )
    route_context = serializers.DictField(
        required=False,
        allow_null=True,
        default=None
    )


class ChatResponseDataSerializer(serializers.Serializer):
    answer = serializers.CharField()
    reply = serializers.CharField(required=False)
    sources = ChatSourceSerializer(many=True, default=list)
    disclaimer = serializers.CharField()
    timestamp = serializers.CharField(required=False)
    has_route_context = serializers.BooleanField(required=False, default=False)


class ChatResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    data = ChatResponseDataSerializer()
