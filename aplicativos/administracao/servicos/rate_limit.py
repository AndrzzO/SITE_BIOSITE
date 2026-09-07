"""Serviço de limitação de taxa (Rate Limiting) para o fluxo de autenticação."""

import hashlib
import logging

from django.core.cache import cache
from django.http import HttpRequest

logger = logging.getLogger("aplicativos.administracao.seguranca")


class ServicoRateLimitLogin:
    """
    Controla e mitiga ataques de força bruta no endpoint de login administrativo.

    Utiliza o cache do Django para contabilizar tentativas inválidas e bloquear
    temporariamente solicitações excedentes a partir de uma combinação de IP e identificador.
    """

    MAX_TENTATIVAS: int = 5
    JANELA_SEGUNDOS: int = 300  # 5 minutos para acumular tentativas
    BLOQUEIO_SEGUNDOS: int = 600  # 10 minutos de bloqueio temporário após exceder limite

    @classmethod
    def obter_ip_cliente(cls, request: HttpRequest) -> str:
        """
        Obtém o endereço IP do cliente.

        Por padrão e segurança imediata, utiliza REMOTE_ADDR para evitar spoofing
        do cabeçalho X-Forwarded-For sem validação prévia de proxies confiáveis.
        """
        ip = request.META.get("REMOTE_ADDR", "")
        return ip.strip() if ip else "127.0.0.1"

    @classmethod
    def _gerar_chave(cls, prefixo: str, ip: str, identificador: str = "") -> str:
        """Gera chave segura e normalizada para o cache usando hash SHA-256."""
        identificador_limpo = identificador.strip().lower()
        conteudo = f"{ip}:{identificador_limpo}".encode()
        hash_digest = hashlib.sha256(conteudo).hexdigest()[:24]
        return f"rate_limit:login:{prefixo}:{hash_digest}"

    @classmethod
    def esta_bloqueado(cls, ip: str, identificador: str = "") -> tuple[bool, int]:
        """
        Verifica se o IP/identificador está atualmente bloqueado.

        Retorna (True, segundos_restantes) ou (False, 0).
        """
        chave_bloqueio = cls._gerar_chave("bloqueado", ip, identificador)
        tempo_expiracao = cache.get(chave_bloqueio)

        if tempo_expiracao is not None:
            return True, int(tempo_expiracao)
        return False, 0

    @classmethod
    def registrar_falha(cls, ip: str, identificador: str = "") -> int:
        """
        Registra uma tentativa falha de login.

        Se o limite de tentativas for atingido, aplica o bloqueio temporário.
        Retorna a quantidade acumulada de tentativas falhas.
        """
        chave_tentativas = cls._gerar_chave("tentativas", ip, identificador)
        tentativas = cache.get(chave_tentativas, 0) + 1
        cache.set(chave_tentativas, tentativas, timeout=cls.JANELA_SEGUNDOS)

        logger.warning(
            "Tentativa falha de autenticação (tentativa %s de %s) para identificador '%s' a partir do IP %s",
            tentativas,
            cls.MAX_TENTATIVAS,
            identificador,
            ip,
        )

        if tentativas >= cls.MAX_TENTATIVAS:
            chave_bloqueio = cls._gerar_chave("bloqueado", ip, identificador)
            cache.set(chave_bloqueio, cls.BLOQUEIO_SEGUNDOS, timeout=cls.BLOQUEIO_SEGUNDOS)
            logger.warning(
                "Bloqueio temporário acionado para identificador '%s' a partir do IP %s por %s segundos",
                identificador,
                ip,
                cls.BLOQUEIO_SEGUNDOS,
            )

        return tentativas

    @classmethod
    def limpar_falhas(cls, ip: str, identificador: str = "") -> None:
        """Limpa as tentativas após um login bem-sucedido."""
        chave_tentativas = cls._gerar_chave("tentativas", ip, identificador)
        chave_bloqueio = cls._gerar_chave("bloqueado", ip, identificador)
        cache.delete(chave_tentativas)
        cache.delete(chave_bloqueio)
