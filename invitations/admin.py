"""Admin Django : outil du développeur pour contrôler les données.

L'admin des mariés (formulaire + aperçu de l'affiche) sera dans Next.js, page /admin.
"""

from django import forms
from django.contrib import admin

from .models import Agent, Expertise, Invite, Mariage, ModeleAffiche, ParametresEcosystem, PhotoJointe, Scan, Table


class ModeleAfficheInline(admin.StackedInline):
    model = ModeleAffiche
    can_delete = False
    fieldsets = [
        ("Affiche envoyée", {"fields": ["type_affiche", "image_complete", "position_qr"]}),
        ("Image", {"fields": ["image_fond"]}),
        ("En-tête", {"fields": ["titre_manuscrit", "titre_principal", "message"]}),
        ("Les mariés", {"fields": ["nom_marie", "liaison", "nom_mariee"]}),
        ("Bandeau", {"fields": ["bandeau_titre", "bandeau_sous_titre"]}),
        ("Date et heure", {"fields": ["jour", "mois_annee", "heure_ceremonie", "moment_ceremonie"]}),
        ("Lieux", {"fields": [
            "lieu_libelle", "lieu_nom", "heure_reception", "moment_reception",
            "reception_libelle", "reception_lieu",
        ]}),
        ("Style", {"fields": [
            ("couleur_titre", "couleur_texte", "couleur_bandeau"),
            ("police_manuscrite", "police_titres", "police_noms", "police_infos"),
        ]}),
    ]


class PhotoJointeInline(admin.TabularInline):
    model = PhotoJointe
    extra = 0
    fields = ["image", "legende", "ordre"]


class TableInline(admin.TabularInline):
    model = Table
    extra = 0


@admin.register(Mariage)
class MariageAdmin(admin.ModelAdmin):
    list_display = ["nom", "date", "proprietaire", "est_actif", "resume"]
    list_filter = ["est_actif"]
    search_fields = ["nom", "slug"]
    prepopulated_fields = {"slug": ["nom"]}
    inlines = [ModeleAfficheInline, PhotoJointeInline, TableInline]

    @admin.display(description="arrivés / places")
    def resume(self, obj):
        s = obj.stats()
        return f"{s['arrives']} / {s['places']}"


@admin.register(ParametresEcosystem)
class ParametresEcosystemAdmin(admin.ModelAdmin):
    list_display = ["nom", "telephone", "whatsapp", "maj_le"]

    def has_add_permission(self, request):
        return not ParametresEcosystem.objects.exists()


@admin.register(Expertise)
class ExpertiseAdmin(admin.ModelAdmin):
    list_display = ["titre", "ordre", "maj_le"]
    list_editable = ["ordre"]
    search_fields = ["titre", "description"]
    ordering = ["ordre", "id"]


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = [
        "nom", "categorie", "mariage", "table", "nombre_places", "personnes_entrees",
        "statut_rsvp", "code_affiche", "arrive_le",
    ]
    list_filter = ["mariage", "categorie", "statut_rsvp", "table"]
    search_fields = ["nom", "telephone", "code"]
    readonly_fields = ["code", "url_qr", "personnes_entrees", "arrive_le", "cree_le", "maj_le"]
    autocomplete_fields = ["mariage"]


class AgentForm(forms.ModelForm):
    nouveau_pin = forms.CharField(
        label="Nouveau PIN",
        required=False,
        min_length=4,
        max_length=8,
        widget=forms.PasswordInput(render_value=False),
        help_text="4 à 8 chiffres. Laisser vide pour garder le PIN actuel.",
    )

    class Meta:
        model = Agent
        fields = ["mariage", "nom", "est_actif"]

    def clean_nouveau_pin(self):
        pin = self.cleaned_data.get("nouveau_pin", "")
        if pin and not pin.isdigit():
            raise forms.ValidationError("Le PIN ne doit contenir que des chiffres.")
        if not pin and not (self.instance and self.instance.pin_hash):
            raise forms.ValidationError("Un PIN est obligatoire pour un nouvel agent.")
        return pin

    def save(self, commit=True):
        agent = super().save(commit=False)
        if self.cleaned_data.get("nouveau_pin"):
            agent.definir_pin(self.cleaned_data["nouveau_pin"])
        if commit:
            agent.save()
        return agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    form = AgentForm
    list_display = ["nom", "mariage", "est_actif"]
    list_filter = ["mariage", "est_actif"]


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    """Journal en lecture seule : on ne modifie pas l'historique des entrées."""

    list_display = ["scanne_le", "resultat", "invite", "personnes", "agent", "mariage"]
    list_filter = ["mariage", "resultat", "agent"]
    search_fields = ["code_lu", "invite__nom"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
