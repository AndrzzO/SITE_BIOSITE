"""
Serviço de geração local de imagens de QR Code para Links Inteligentes (Prompt 10).
"""

import io
import logging

import qrcode
import qrcode.constants
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image

from .models import LinkInteligente
from .servicos_links import obter_url_completa_link

logger = logging.getLogger("aplicativos.sites.servicos_qrcode")

TAMANHOS_PERMITIDOS_QR = {256, 512, 1024, 2048}


def gerar_imagem_qrcode(
    link: LinkInteligente,
    tamanho: int = 512,
    formato: str = "PNG",
    request=None,
) -> bytes:
    """
    Gera localmente uma imagem de QR Code de alta fidelidade e legibilidade.

    REGRAS ARQUITETURAIS:
    1. Codifica EXCLUSIVAMENTE a URL inteligente oficial (ex: https://go.site.com/q/<token>/),
       NUNCA a URL direta final do cliente.
    2. Alto contraste (preto sobre branco) e margem de silêncio (quiet zone border=4) obrigatória.
    3. Nível de correção de erro M (~15%) para leitura rápida e confiável mesmo em telas ou impressão.
    4. Validação estrita de dimensões contra allowlist de segurança.
    """
    if tamanho not in TAMANHOS_PERMITIDOS_QR:
        raise ValidationError(
            _(
                f"Tamanho inválido para geração de QR Code. Permitidos: {sorted(TAMANHOS_PERMITIDOS_QR)}."
            )
        )

    # Obtém a URL do smart link correspondente
    url_inteligente = obter_url_completa_link(link, request=request)

    qr = qrcode.QRCode(
        version=None,  # Ajuste automático de versão para densidade ideal
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,  # Margem quieta padrão ISO/IEC 18004
    )
    qr.add_data(url_inteligente)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Converte para formato PIL Image padrão e redimensiona para tamanho exato
    img_pil = img.get_image()
    if img_pil.size != (tamanho, tamanho):
        img_pil = img_pil.resize((tamanho, tamanho), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img_pil.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
