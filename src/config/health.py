from django.conf import settings
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from redis import Redis
from redis.exceptions import RedisError


def _database_ready() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except DatabaseError:
        return False


def _redis_ready() -> bool:
    client = Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=1,
        socket_timeout=1,
    )

    try:
        return bool(client.ping())
    except (RedisError, OSError):
        return False
    finally:
        client.close()


def health_live(_request: HttpRequest) -> HttpResponse:
    return JsonResponse({"status": "ok"})


def health_ready(_request: HttpRequest) -> HttpResponse:
    if _database_ready() and _redis_ready():
        return JsonResponse({"status": "ready"})

    return JsonResponse({"status": "unavailable"}, status=503)
