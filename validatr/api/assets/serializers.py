from django.urls import path, include
from validatr.api.models import Asset, FILE_PROVIDERS

from rest_framework import routers, serializers, viewsets


class NotificationURLSerializer(serializers.Serializer):
    onStart = serializers.CharField(required=False)
    onSuccess = serializers.CharField(required=False)
    onFailure = serializers.CharField(required=False)


class AssetPathSerializer(serializers.Serializer):
    location = serializers.ChoiceField(choices=FILE_PROVIDERS, required=True)
    path = serializers.CharField(required=True)


class CreateAssetRequestSerializer(serializers.Serializer):
    assetPath = AssetPathSerializer(required=True)
    notifications = NotificationURLSerializer(required=True)


class GetAssetResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = (
            "id",
            "state",
        )


class GetAssetWithErrorsResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = (
            "id",
            "state",
            "errors",
        )
