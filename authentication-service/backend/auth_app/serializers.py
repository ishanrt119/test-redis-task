from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    password = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username is None or password is None or not username.strip() or not password.strip():
            raise serializers.ValidationError('Username and password are required')

        return attrs
