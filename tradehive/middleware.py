import redis
from django.http import JsonResponse
from django.conf import settings

from users.models import SuspiciousRequest

r = redis.StrictRedis.from_url(settings.CACHES["default"]["LOCATION"])


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = self.get_client_ip(request)
        limit_key = f"rate-limit:{client_ip}"

        current_count = r.incr(limit_key)
        if current_count == 1:
            r.expire(limit_key, 1)
        if current_count > 10:
            SuspiciousRequest.objects.create(ip_address=client_ip, url=request.path, user_agent=request.META.get("HTTP_USER_AGENT", ""))
            return JsonResponse({"detail": "Too Many Requests"}, status=429)

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
