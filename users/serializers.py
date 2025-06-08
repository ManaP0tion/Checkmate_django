# users/serializers.py

from rest_framework import serializers
from .models import User

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username = data['username']
        password = data['password']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("사용자를 찾을 수 없습니다.")

        if not user.check_password(password):
            raise serializers.ValidationError("비밀번호가 틀렸습니다.")

        data['user'] = user
        return data

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'role',
            'name',
            'major',
            'department',
        ]

    def validate(self, data):
        role = data.get('role')

        if role == 'student':
            if not data.get('username'):
                raise serializers.ValidationError("학생은 학번(username)이 필수입니다.")
            if not data.get('major'):
                raise serializers.ValidationError("학생은 전공이 필수입니다.")

        elif role == 'professor':
            if not data.get('username'):
                raise serializers.ValidationError("교수는 교수번호(username)가 필수입니다.")
            if not data.get('department'):
                raise serializers.ValidationError("교수는 학과가 필수입니다.")

        else:
            raise serializers.ValidationError("역할(role)이 잘못되었습니다.")

        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'email', 'role']