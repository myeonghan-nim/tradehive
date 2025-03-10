import redis
from django.http import JsonResponse
from django.conf import settings

from users.models import SuspiciousRequest

r = redis.StrictRedis.from_url(settings.CACHES["default"]["LOCATION"])


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    # middleware가 실행될 때마다 호출되는 함수
    def __call__(self, request):
        client_ip = self.get_client_ip(request)
        limit_key = f"rate-limit:{client_ip}"

        # incr() 함수를 사용하여 key에 해당하는 value를 1씩 증가시키고, 현재 value를 반환
        current_count = r.incr(limit_key)
        if current_count == 1:
            # key에 대한 TTL(Time To Live)을 설정
            r.expire(limit_key, 1)
        if current_count > 10:
            # SuspiciousRequest 모델에 단기간에 너무 많은 요청을 보낸 IP 주소를 저장
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
