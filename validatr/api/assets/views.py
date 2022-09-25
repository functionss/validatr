import datetime
from django.shortcuts import get_object_or_404, get_list_or_404
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework import filters

from validatr.api.models import Asset
from validatr.api.assets.serializers import (
    CreateAssetRequestSerializer,
    GetAssetResponseSerializer,
    GetAssetWithErrorsResponseSerializer,
)

from validatr.pipeline.tasks import run_pipeline


class AssetViewset(viewsets.ViewSet, viewsets.GenericViewSet):

    queryset = Asset.objects.all()
    serializer_class = GetAssetResponseSerializer

    def list(self, request):
        """
        List of image assets.

        GET /api/assets
        """
        query = self.get_queryset()
        serializer = GetAssetWithErrorsResponseSerializer(query, many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        fetch a specific asset by ID

        GET /api/assets/{asset_id}
        """
        query = self.queryset.filter(id=pk)

        asset = get_object_or_404(query)

        if asset.errors:
            serializer = GetAssetWithErrorsResponseSerializer(asset)
        else:
            serializer = GetAssetResponseSerializer(asset)

        return Response(serializer.data)

    @action(methods=["post"], url_path="image", detail=False)
    def create_asset(self, request):
        """
        Create a new image asset

        POST /api/assets/image/
        """
        serializer = CreateAssetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # create asset
        asset = Asset.objects.create(
            path=data["assetPath"]["path"],
            provider=data["assetPath"]["location"],
            start_webhook_endpoint=data["notifications"]["onStart"],
            success_webhook_endpoint=data["notifications"]["onSuccess"],
            failure_webhook_endpoint=data["notifications"]["onFailure"],
            state="queued",
        )

        resp = GetAssetResponseSerializer(asset).data

        run_pipeline(asset.id)
        return Response(resp, status=status.HTTP_202_ACCEPTED)
