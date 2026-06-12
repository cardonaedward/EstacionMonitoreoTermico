from rest_framework import serializers

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    codigo = serializers.CharField(max_length=4, min_length=4, required=True)
    nueva_password = serializers.CharField(min_length=8, required=True)

    def validate_codigo(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El código debe ser numérico.")
        return value