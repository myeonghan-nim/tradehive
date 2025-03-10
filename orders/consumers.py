import json

from channels.generic.websocket import AsyncWebsocketConsumer


# AsyncWebsocketConsumer는 WebSocket 연결을 처리하는 클래스
# connect, disconnect, receive 메서드를 오버라이드하여 WebSocket 연결을 처리
class TradeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.symbol = self.scope["url_route"]["kwargs"]["symbol"]
        self.group_name = f"orders_{self.symbol}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def send_trade_data(self, event):
        trade_data = event["data"]
        await self.send(text_data=json.dumps(trade_data))
