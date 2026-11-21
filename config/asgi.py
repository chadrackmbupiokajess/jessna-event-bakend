"""Point d'entrée ASGI (facultatif) : Django seul, sans WebSocket.

Le temps réel passe par des requêtes AJAX régulières (voir /api/mariages/<id>/direct/).
`python manage.py runserver` utilise wsgi.py ; ce fichier sert seulement si un
serveur ASGI (uvicorn, hypercorn…) est utilisé un jour en production.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
