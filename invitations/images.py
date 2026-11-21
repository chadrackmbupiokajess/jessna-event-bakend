"""Conversion et compression automatiques des images envoyées (fond et affiche prête).

Une photo de téléphone (HEIC converti, PNG de 5 Mo, JPEG de 4000 px…) devient un
JPEG progressif, à la bonne taille pour l'affiche, sans perte visible :
- l'orientation du téléphone (EXIF) est appliquée, puis les métadonnées (GPS…) retirées ;
- l'image est réduite seulement si elle dépasse 2 fois la taille de l'affiche
  (1059 × 1486 px), ce qui reste net même sur un écran Retina ou en zoom ;
- qualité 90 avec couleurs pleine résolution (pas de sous-échantillonnage) :
  les petits textes d'une affiche déjà prête restent nets ;
- la transparence (PNG) est posée sur un fond uni ;
- si l'image d'origine était déjà plus légère, elle est gardée telle quelle.
"""

from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

# 2 × la taille de l'affiche : net partout, même agrandie à 200 %.
COTE_MAX = (2 * 1059, 2 * 1486)
QUALITE = 90


def optimiser_image(fichier, fond_transparent=(255, 255, 255)) -> InMemoryUploadedFile:
    """Renvoie un JPEG optimisé, prêt à être enregistré dans un ImageField."""
    try:
        fichier.seek(0)
        image = Image.open(fichier)
        image.load()
    except (UnidentifiedImageError, OSError):
        raise serializers.ValidationError("Ce fichier n'est pas une image lisible (JPEG, PNG ou WebP).")

    taille_origine = getattr(fichier, "size", None)
    format_origine = (image.format or "").upper()

    tournee = image.getexif().get(0x0112, 1) not in (0, 1)
    image = ImageOps.exif_transpose(image)  # photo prise de travers → remise droite
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        fond = Image.new("RGB", image.size, fond_transparent)
        fond.paste(image, mask=image.getchannel("A"))
        image = fond
    elif image.mode != "RGB":
        image = image.convert("RGB")

    reduite = image.width > COTE_MAX[0] or image.height > COTE_MAX[1]
    if reduite:
        image.thumbnail(COTE_MAX, Image.Resampling.LANCZOS)

    sortie = BytesIO()
    image.save(sortie, "JPEG", quality=QUALITE, subsampling=0, optimize=True, progressive=True)

    # Un JPEG déjà léger et à la bonne taille : on ne le recompresse pas.
    if format_origine == "JPEG" and not reduite and not tournee and taille_origine and taille_origine <= sortie.tell():
        fichier.seek(0)
        return fichier

    nom = f"{Path(getattr(fichier, 'name', 'image')).stem[:60] or 'image'}.jpg"
    sortie.seek(0)
    return InMemoryUploadedFile(sortie, None, nom, "image/jpeg", sortie.getbuffer().nbytes, None)
