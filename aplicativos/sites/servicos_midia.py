"""Serviços de validação, sanitização EXIF e processamento seguro de imagens para BioSites."""

import io
import os
import uuid
from typing import BinaryIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import MidiaSite, ProjetoSite

MAX_TAMANHO_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DIMENSAO_PX = 5000  # Máximo de 5000x5000px
LARGURA_MAXIMA_MOBILE = 1200  # Redimensionamento suave para telas mobile

EXTENSOES_PERMITIDAS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
MIME_TYPES_PERMITIDOS = frozenset({"image/jpeg", "image/png", "image/webp"})


def validar_arquivo_imagem(arquivo_upload: UploadedFile) -> None:
    """Valida o tamanho, extensão e integridade real de bytes do arquivo de imagem."""
    if not arquivo_upload:
        raise ValidationError(_("Nenhum arquivo enviado."))

    if arquivo_upload.size > MAX_TAMANHO_BYTES:
        raise ValidationError(
            _("O arquivo excede o limite máximo permitido de %(max)s MB."),
            params={"max": MAX_TAMANHO_BYTES // (1024 * 1024)},
        )

    nome_arquivo = arquivo_upload.name or ""
    nome_base, extensao = os.path.splitext(nome_arquivo.lower())

    if extensao == ".svg":
        raise ValidationError(
            _("Arquivos SVG não são permitidos por motivos de segurança e integridade visual.")
        )

    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValidationError(
            _("Formato de arquivo não suportado (%(ext)s). Use apenas JPEG, PNG ou WebP."),
            params={"ext": extensao},
        )

    # Validação real dos bytes com Pillow (prevenção de executáveis com extensão forjada)
    posicao_inicial = arquivo_upload.tell()
    try:
        arquivo_upload.seek(0)
        with Image.open(arquivo_upload) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as err:
        raise ValidationError(
            _("O arquivo enviado não é uma imagem válida ou está corrompido.")
        ) from err
    finally:
        arquivo_upload.seek(posicao_inicial)


def processar_e_otimizar_imagem(
    stream_arquivo: BinaryIO,
    largura_maxima: int = LARGURA_MAXIMA_MOBILE,
    qualidade: int = 85,
) -> tuple[bytes, int, int]:
    """
    Processa a imagem para uso web mobile-first:
    1. Corrige a rotação conforme orientação EXIF.
    2. Remove metadados EXIF desnecessários (privacidade e peso).
    3. Redimensiona suavemente se exceder a largura máxima.
    4. Converte para formato WebP otimizado.

    Retorna (bytes_processados, largura, altura).
    """
    stream_arquivo.seek(0)
    with Image.open(stream_arquivo) as img:
        # Rejeição de dimensões extremas antes de descompactar totalmente
        if img.width > MAX_DIMENSAO_PX or img.height > MAX_DIMENSAO_PX:
            raise ValidationError(
                _("Dimensões da imagem excedem o limite de %(max)spx."),
                params={"max": MAX_DIMENSAO_PX},
            )

        # Correção da rotação baseada no EXIF original
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # Se não houver EXIF ou for inválido, mantém original

        # Converte para RGB ou RGBA dependendo da presença de canal alfa
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        # Redimensionamento proporcional para mobile se necessário
        largura_atual, altura_atual = img.size
        if largura_atual > largura_maxima:
            fator = largura_maxima / float(largura_atual)
            nova_altura = max(1, int(float(altura_atual) * fator))
            img = img.resize((largura_maxima, nova_altura), Image.Resampling.LANCZOS)
            largura_atual, altura_atual = img.size

        # Salva em buffer WebP removendo completamente os metadados EXIF
        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=qualidade, method=6)
        bytes_finais = buffer.getvalue()

        return bytes_finais, largura_atual, altura_atual


def criar_midia_projeto(
    projeto: ProjetoSite,
    arquivo_upload: UploadedFile,
    tipo: str = MidiaSite.Tipo.IMAGEM,
) -> MidiaSite:
    """Valida, otimiza e persiste uma nova imagem vinculada ao projeto."""
    validar_arquivo_imagem(arquivo_upload)

    bytes_otimizados, largura, altura = processar_e_otimizar_imagem(arquivo_upload)

    nome_seguro = f"{uuid.uuid4().hex}.webp"
    arquivo_conteudo = ContentFile(bytes_otimizados, name=nome_seguro)

    midia = MidiaSite(
        projeto=projeto,
        arquivo=arquivo_conteudo,
        nome_original=arquivo_upload.name or "imagem.webp",
        mime_type="image/webp",
        tamanho_bytes=len(bytes_otimizados),
        largura=largura,
        altura=altura,
        tipo=tipo,
    )
    midia.save()
    return midia
