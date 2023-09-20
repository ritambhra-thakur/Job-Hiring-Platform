from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path, re_path

import notification.routing
from notification import consumers

application = ProtocolTypeRouter({
	'websocket': AllowedHostsOriginValidator(
		AuthMiddlewareStack(
			URLRouter([
					# path("send/", SendNotification.as_view()),
                    path("ws/notification/<str:grp_name>/", consumers.ChatConsumer.as_asgi())
			])
		)
	),
})
