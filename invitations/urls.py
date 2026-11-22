from django.urls import path

from . import scan_views, views

urlpatterns = [
    # Scanner de l'agent : lien /scan/<slug> + code PIN, puis jeton X-Agent-Token
    path("scan/mariage/<slug:slug>/", scan_views.ScanMariageView.as_view()),
    path("scan/mariage/<slug:slug>/connexion/", scan_views.ScanConnexionView.as_view()),
    path("scan/verifier/", scan_views.ScanVerifierView.as_view()),
    path("scan/valider/", scan_views.ScanValiderView.as_view()),
    path("scan/stats/", scan_views.ScanStatsView.as_view()),
    # Connexion (administrateur et mariés)
    path("auth/csrf/", views.CsrfView.as_view()),
    path("auth/connexion/", views.ConnexionView.as_view()),
    path("auth/deconnexion/", views.DeconnexionView.as_view()),
    path("auth/moi/", views.MoiView.as_view()),
    # Administrateur : tous les mariages, création du mariage + compte des mariés
    path("admin/mariages/", views.AdminMariagesView.as_view()),
    path("admin/ecosysteme/", views.AdminEcosystemView.as_view()),
    path("admin/ecosysteme/expertises/", views.AdminExpertisesView.as_view()),
    path("admin/ecosysteme/expertises/<int:expertise_id>/", views.AdminExpertiseDetailView.as_view()),
    path("admin/mariages/<int:mariage_id>/mot-de-passe/", views.AdminMotDePasseView.as_view()),
    # Espace d'un mariage (les mariés, ou l'administrateur)
    path("mariages/", views.MesMariagesView.as_view()),
    path("mariages/<int:mariage_id>/", views.MariageDetailView.as_view()),
    path("mariages/<int:mariage_id>/affiche/", views.AfficheView.as_view()),
    path("mariages/<int:mariage_id>/affiche/image-origine/", views.AfficheImageOrigineView.as_view()),
    path("mariages/<int:mariage_id>/invites/", views.InvitesView.as_view()),
    path("mariages/<int:mariage_id>/invites/<int:pk>/", views.InviteDetailView.as_view()),
    path("mariages/<int:mariage_id>/invites/<int:pk>/envoyee/", views.InviteEnvoyeeView.as_view()),
    path("mariages/<int:mariage_id>/invites/<int:pk>/image/", views.InviteImageView.as_view()),
    path("mariages/<int:mariage_id>/presence/", views.PresenceView.as_view()),
    path("mariages/<int:mariage_id>/direct/", views.DirectView.as_view()),
    path("mariages/<int:mariage_id>/photos/", views.PhotosView.as_view()),
    path("mariages/<int:mariage_id>/photos/<int:pk>/", views.PhotoDetailView.as_view()),
    path("mariages/<int:mariage_id>/agents/", views.AgentsView.as_view()),
    path("mariages/<int:mariage_id>/agents/<int:pk>/", views.AgentDetailView.as_view()),
    # Public : l'invité ouvre son invitation avec le code du QR
    path("public/invitations/<str:code>/", views.InvitationPubliqueView.as_view()),
]
