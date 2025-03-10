from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"

    def ready(self):
        # signals는 모델이 로드되었을 때만 작동하므로 AppConfig의 ready() 메서드를 사용해야 함
        import orders.signals  # noqa

        return super().ready()
