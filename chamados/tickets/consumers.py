import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chamado, Atualizacao

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chamado_id = self.scope['url_route']['kwargs']['chamado_id']
        self.room_group_name = f'chat_{self.chamado_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        texto = text_data_json.get('texto', '')
        documento_url = text_data_json.get('documento_url', '')

        # Salvar a mensagem no banco
        atualizacao = await self.save_message(texto, documento_url)

        # Enviar mensagem para o grupo
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'texto': texto,
                'documento_url': documento_url,
                'autor': self.scope['user'].username,
                'criado_em': atualizacao.criado_em.strftime('%Y-%m-%d %H:%M:%S'),
                'is_autor': False,  # Verificado no cliente
            }
        )

    async def chat_message(self, event):
        # Enviar mensagem para o WebSocket
        is_autor = self.scope['user'].username == event['autor']
        await self.send(text_data=json.dumps({
            'texto': event['texto'],
            'documento_url': event['documento_url'],
            'autor': event['autor'],
            'criado_em': event['criado_em'],
            'is_autor': is_autor,
        }))

    @database_sync_to_async
    def save_message(self, texto, documento_url):
        chamado = Chamado.objects.get(id=self.chamado_id)
        atualizacao = Atualizacao.objects.create(
            chamado=chamado,
            texto=texto,
            autor=self.scope['user']
        )
        if documento_url:
            atualizacao.documento.name = documento_url  # Define o caminho do documento
            atualizacao.save()
        return atualizacao