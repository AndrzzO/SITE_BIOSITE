"""Definição e dados estruturados dos 8 Templates e 15 Blocos iniciais do Sistema (Prompt 7)."""

from typing import Any

TEMPLATES_SISTEMA: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. BioSite Minimal
    # -------------------------------------------------------------------------
    {
        "nome": "BioSite Minimal",
        "slug": "biosite-minimal",
        "categoria": "biosite",
        "descricao": "Design limpo, moderno e com espaçamento arejado, ideal para criadores, consultores e perfis pessoais focados em simplicidade e elegância.",
        "ordem": 10,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#0f172a",
                "cor_secundaria": "#475569",
                "cor_fundo": "#ffffff",
                "cor_superficie": "#f8fafc",
                "cor_texto": "#0f172a",
                "cor_texto_secundario": "#64748b",
                "fonte_principal": "Inter, sans-serif",
                "fonte_titulos": "Inter, sans-serif",
                "radius_padrao": "12px",
                "sombra_padrao": "suave",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Apresentação",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 24, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Foto de Perfil",
                                                "forma": "circulo",
                                                "tamanho": 100,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {"texto": "Seu Nome", "nivel": "h1"},
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 24,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Consultor Estratégico & Especialista Digital. Ajudando empresas a crescer com solidez."
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#64748b",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Canais de Contato",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 12, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 12}},
                                    "elementos": [
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá! Gostaria de falar com você.",
                                                "texto": "Falar no WhatsApp",
                                                "estilo_botao": "solido",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "website",
                                            "conteudo": {
                                                "url": "https://meubiosite.com.br",
                                                "texto": "Acessar Meu Website Oficial",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "redes_sociais",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "rede": "instagram",
                                                        "url": "https://instagram.com/perfil",
                                                    },
                                                    {
                                                        "rede": "linkedin",
                                                        "url": "https://linkedin.com/in/perfil",
                                                    },
                                                    {
                                                        "rede": "youtube",
                                                        "url": "https://youtube.com/@perfil",
                                                    },
                                                ],
                                                "formato": "icones",
                                            },
                                        },
                                        {
                                            "tipo": "divisor",
                                            "conteudo": {
                                                "estilo": "solid",
                                                "espessura": 1,
                                                "largura": "80%",
                                                "espacamento": 16,
                                            },
                                        },
                                        {
                                            "tipo": "mapa",
                                            "conteudo": {
                                                "endereco": "Av. Paulista, 1000 - São Paulo, SP",
                                                "texto": "📍 Ver Endereço do Escritório",
                                                "largura_total": True,
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 2. BioSite Premium
    # -------------------------------------------------------------------------
    {
        "nome": "BioSite Premium",
        "slug": "biosite-premium",
        "categoria": "biosite",
        "descricao": "Visual dark moderno com iluminação neon sutil, cards de serviços em destaque, galeria de fotos e múltiplos canais de conversão.",
        "ordem": 20,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#38bdf8",
                "cor_secundaria": "#818cf8",
                "cor_fundo": "#0b0f19",
                "cor_superficie": "#111827",
                "cor_texto": "#f8fafc",
                "cor_texto_secundario": "#94a3b8",
                "fonte_principal": "Plus Jakarta Sans, sans-serif",
                "fonte_titulos": "Plus Jakarta Sans, sans-serif",
                "radius_padrao": "16px",
                "sombra_padrao": "glow",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Perfil Hero",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 28, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Avatar VIP",
                                                "forma": "circulo",
                                                "tamanho": 110,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Dra. Juliana Mendes",
                                                "nivel": "h1",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 26,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Medicina Integrativa & Longevidade Saudável"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 15,
                                                    "cor_texto": "#38bdf8",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Chamada Rápida",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 10}},
                                    "elementos": [
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá! Gostaria de agendar uma consulta.",
                                                "texto": "Agendar Consulta no WhatsApp",
                                                "estilo_botao": "flutuante",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "agendamento_externo",
                                            "conteudo": {
                                                "url": "https://calendar.google.com/",
                                                "texto": "📅 Horários Disponíveis na Agenda",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "redes_sociais",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "rede": "instagram",
                                                        "url": "https://instagram.com/perfil",
                                                    },
                                                    {
                                                        "rede": "youtube",
                                                        "url": "https://youtube.com/@perfil",
                                                    },
                                                    {
                                                        "rede": "whatsapp",
                                                        "url": "https://wa.me/5511999999999",
                                                    },
                                                ],
                                                "formato": "icones",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Serviços em Destaque",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 12, "padding_baixo": 20}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {}},
                                    "elementos": [
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Planos de Acompanhamento",
                                                "nivel": "h3",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 18,
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "servicos",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "titulo": "Consulta Inicial & Check-up",
                                                        "descricao": "Avaliação clínica abrangente com mapeamento metabólico completo.",
                                                        "preco": "R$ 450",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Reservar Vaga",
                                                    },
                                                    {
                                                        "titulo": "Programa Longevidade 360",
                                                        "descricao": "Acompanhamento bimestral com plano nutricional e suporte contínuo.",
                                                        "preco": "R$ 1.200",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Saber Mais",
                                                    },
                                                ],
                                                "layout": "cards",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 3. Cartão Digital NFC
    # -------------------------------------------------------------------------
    {
        "nome": "Cartão Digital NFC",
        "slug": "cartao-digital-nfc",
        "categoria": "cartao_digital",
        "descricao": "Otimizado para aproximação por tag NFC e troca ágil de contatos profissionais, com botões diretos de ligação, WhatsApp e e-mail.",
        "ordem": 30,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#2563eb",
                "cor_secundaria": "#3b82f6",
                "cor_fundo": "#f8fafc",
                "cor_superficie": "#ffffff",
                "cor_texto": "#1e293b",
                "cor_texto_secundario": "#64748b",
                "fonte_principal": "Inter, sans-serif",
                "fonte_titulos": "Inter, sans-serif",
                "radius_padrao": "12px",
                "sombra_padrao": "media",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Cartão de Visitas",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 24, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Foto do Profissional",
                                                "forma": "arredondado",
                                                "tamanho": 100,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Carlos Eduardo Silva",
                                                "nivel": "h1",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 24,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Diretor de Relações Corporativas | Nexus Bank"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#2563eb",
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "divisor",
                                            "conteudo": {
                                                "estilo": "solid",
                                                "espessura": 1,
                                                "largura": "90%",
                                                "espacamento": 16,
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Ações Imediatas",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 10}},
                                    "elementos": [
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá Carlos! Peguei seu contato pelo cartão NFC.",
                                                "texto": "Conversar no WhatsApp",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "telefone",
                                            "conteudo": {
                                                "numero": "(11) 99999-9999",
                                                "texto": "Ligar no Celular",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "email",
                                            "conteudo": {
                                                "email": "carlos.silva@nexusbank.com",
                                                "texto": "Enviar E-mail Corporativo",
                                                "assunto": "Contato via Cartão NFC",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "website",
                                            "conteudo": {
                                                "url": "https://nexusbank.com",
                                                "texto": "Visitar Portal da Empresa",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "redes_sociais",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "rede": "linkedin",
                                                        "url": "https://linkedin.com/in/perfil",
                                                    },
                                                    {
                                                        "rede": "instagram",
                                                        "url": "https://instagram.com/perfil",
                                                    },
                                                ],
                                                "formato": "botoes",
                                            },
                                        },
                                        {
                                            "tipo": "mapa",
                                            "conteudo": {
                                                "endereco": "Av. Faria Lima, 2500 - Itaim Bibi, São Paulo - SP",
                                                "texto": "Localização da Sede",
                                                "largura_total": True,
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 4. Profissional Moderno
    # -------------------------------------------------------------------------
    {
        "nome": "Profissional Moderno",
        "slug": "profissional-moderno",
        "categoria": "profissional",
        "descricao": "Estrutura completa para médicos, dentistas, advogados, consultores e especialistas liberais com apresentação de serviços e agendamento.",
        "ordem": 40,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#0d9488",
                "cor_secundaria": "#14b8a6",
                "cor_fundo": "#ffffff",
                "cor_superficie": "#f0fdfa",
                "cor_texto": "#134e4a",
                "cor_texto_secundario": "#0f766e",
                "fonte_principal": "Plus Jakarta Sans, sans-serif",
                "fonte_titulos": "Plus Jakarta Sans, sans-serif",
                "radius_padrao": "12px",
                "sombra_padrao": "suave",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Apresentação & Autoridade",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 24, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Doutor / Consultor",
                                                "forma": "circulo",
                                                "tamanho": 105,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Dr. Fernando Duarte",
                                                "nivel": "h1",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 24,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Advocacia Empresarial & Assessoria Tributária"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#0d9488",
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Mais de 15 anos defendendo o patrimônio e os direitos de empresas de tecnologia e comércio."
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 13,
                                                    "cor_texto": "#4b5563",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Serviços & Atuação",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 12, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {}},
                                    "elementos": [
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Áreas de Atuação",
                                                "nivel": "h3",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 18,
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "servicos",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "titulo": "Planejamento Tributário Estratégico",
                                                        "descricao": "Redução legal de carga tributária e recuperação de créditos judiciais.",
                                                        "preco": "Sob Consulta",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Solicitar Proposta",
                                                    },
                                                    {
                                                        "titulo": "Contratos & Negociações Comerciais",
                                                        "descricao": "Elaboração, blindagem jurídica e revisão de parcerias e fusões.",
                                                        "preco": "Sob Consulta",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Falar com Advogado",
                                                    },
                                                ],
                                                "layout": "cards",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Agendamento & Endereço",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 10}},
                                    "elementos": [
                                        {
                                            "tipo": "agendamento_externo",
                                            "conteudo": {
                                                "url": "https://calendar.google.com/",
                                                "texto": "Agendar Reunião Inicial",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá Dr. Fernando! Preciso de assessoria jurídica.",
                                                "texto": "WhatsApp do Escritório",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "mapa",
                                            "conteudo": {
                                                "endereco": "Av. Brigadeiro Luis Antonio, 3000 - Jardim Paulista, São Paulo - SP",
                                                "texto": "Endereço do Escritório",
                                                "largura_total": True,
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 5. Profissional Elegante
    # -------------------------------------------------------------------------
    {
        "nome": "Profissional Elegante",
        "slug": "profissional-elegante",
        "categoria": "profissional",
        "descricao": "Estilo editorial refinado com tipografia serifada sofisticada, tons neutros quentes e layout espaçado de alto padrão.",
        "ordem": 50,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#78350f",
                "cor_secundaria": "#92400e",
                "cor_fundo": "#fefce8",
                "cor_superficie": "#fffbeb",
                "cor_texto": "#451a03",
                "cor_texto_secundario": "#78350f",
                "fonte_principal": "Inter, sans-serif",
                "fonte_titulos": "Playfair Display, serif",
                "radius_padrao": "8px",
                "sombra_padrao": "suave",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Monograma & Perfil",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 32, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Monograma Pessoal",
                                                "forma": "circulo",
                                                "tamanho": 95,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {"texto": "Helena Vianna", "nivel": "h1"},
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 28,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Arquitetura de Interiores & Design Sensorial"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#78350f",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "divisor",
                                            "conteudo": {
                                                "estilo": "solid",
                                                "espessura": 1,
                                                "largura": "60%",
                                                "espacamento": 20,
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "“Espaços que inspiram calma, autenticidade e conexão humana em cada detalhe.”"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#57534e",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Especialidades",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 12, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 12}},
                                    "elementos": [
                                        {
                                            "tipo": "servicos",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "titulo": "Projetos Residenciais Exclusivos",
                                                        "descricao": "Concepção do conceito à entrega das chaves com acompanhamento rigoroso de obra.",
                                                        "preco": "Consulte",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Conversar",
                                                    },
                                                    {
                                                        "titulo": "Consultoria de Ambientes & Curadoria",
                                                        "descricao": "Transformação expressa de interiores com foco em iluminação e mobiliário autoral.",
                                                        "preco": "Consulte",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Conversar",
                                                    },
                                                ],
                                                "layout": "cards",
                                            },
                                        },
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá Helena! Gostaria de conversar sobre um projeto.",
                                                "texto": "Falar Diretamente com Helena",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "redes_sociais",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "rede": "instagram",
                                                        "url": "https://instagram.com/perfil",
                                                    },
                                                    {
                                                        "rede": "linkedin",
                                                        "url": "https://linkedin.com/in/perfil",
                                                    },
                                                ],
                                                "formato": "icones",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 6. Empresa Compacta
    # -------------------------------------------------------------------------
    {
        "nome": "Empresa Compacta",
        "slug": "empresa-compacta",
        "categoria": "empresa",
        "descricao": "Solução institucional para pequenas e médias empresas, estúdios e agências apresentarem seus diferenciais, catálogo e canais de atendimento.",
        "ordem": 60,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#1e40af",
                "cor_secundaria": "#3b82f6",
                "cor_fundo": "#ffffff",
                "cor_superficie": "#f1f5f9",
                "cor_texto": "#0f172a",
                "cor_texto_secundario": "#475569",
                "fonte_principal": "Poppins, sans-serif",
                "fonte_titulos": "Poppins, sans-serif",
                "radius_padrao": "12px",
                "sombra_padrao": "suave",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Identidade da Empresa",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 24, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Logotipo da Empresa",
                                                "forma": "arredondado",
                                                "tamanho": 100,
                                                "borda": False,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Vanguard Soluções",
                                                "nivel": "h1",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 24,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Transformação Digital e Tecnologia Sob Medida para o seu Negócio."
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#475569",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Soluções & Portfólio",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 12, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {}},
                                    "elementos": [
                                        {
                                            "tipo": "servicos",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "titulo": "Sistemas Web & Mobile",
                                                        "descricao": "Aplicações escaláveis desenvolvidas com segurança e alta performance.",
                                                        "preco": "Sob Medida",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Pedir Orçamento",
                                                    },
                                                    {
                                                        "titulo": "Cloud & Infraestrutura",
                                                        "descricao": "Migração, monitoramento contínuo e suporte técnico 24/7.",
                                                        "preco": "Sob Medida",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Pedir Orçamento",
                                                    },
                                                ],
                                                "layout": "cards",
                                            },
                                        },
                                        {
                                            "tipo": "galeria",
                                            "conteudo": {
                                                "layout": "grid",
                                                "colunas": 2,
                                                "imagens": [
                                                    {"url": "", "alt": "Projeto 1"},
                                                    {"url": "", "alt": "Projeto 2"},
                                                ],
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Atendimento Comercial",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 10}},
                                    "elementos": [
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá! Gostaria de um orçamento para minha empresa.",
                                                "texto": "Falar com Consultor Comercial",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "email",
                                            "conteudo": {
                                                "email": "comercial@vanguard.com.br",
                                                "texto": "Enviar Briefing por E-mail",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "mapa",
                                            "conteudo": {
                                                "endereco": "Rua Gomes de Carvalho, 1500 - Vila Olímpia, São Paulo - SP",
                                                "texto": "📍 Nosso Escritório",
                                                "largura_total": True,
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 7. Portfólio Visual
    # -------------------------------------------------------------------------
    {
        "nome": "Portfólio Visual",
        "slug": "portfolio-visual",
        "categoria": "portfolio",
        "descricao": "Focado no impacto visual para fotógrafos, designers, arquitetos e artistas visuais, priorizando galerias e amostras de trabalhos.",
        "ordem": 70,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#6366f1",
                "cor_secundaria": "#a855f7",
                "cor_fundo": "#090d16",
                "cor_superficie": "#131826",
                "cor_texto": "#f8fafc",
                "cor_texto_secundario": "#94a3b8",
                "fonte_principal": "Plus Jakarta Sans, sans-serif",
                "fonte_titulos": "Plus Jakarta Sans, sans-serif",
                "radius_padrao": "12px",
                "sombra_padrao": "glow",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Apresentação Criativa",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 28, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Criador Visual",
                                                "forma": "circulo",
                                                "tamanho": 100,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {"texto": "Lucas Moretti", "nivel": "h1"},
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 26,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Fotografia Autoral & Direção Criativa"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#a855f7",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Galeria de Trabalhos",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 20}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {}},
                                    "elementos": [
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Trabalhos Selecionados",
                                                "nivel": "h3",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 18,
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "galeria",
                                            "conteudo": {
                                                "layout": "grid",
                                                "colunas": 3,
                                                "imagens": [
                                                    {"url": "", "alt": "Obra 1"},
                                                    {"url": "", "alt": "Obra 2"},
                                                    {"url": "", "alt": "Obra 3"},
                                                    {"url": "", "alt": "Obra 4"},
                                                    {"url": "", "alt": "Obra 5"},
                                                    {"url": "", "alt": "Obra 6"},
                                                ],
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Contato & Orçamentos",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 10}},
                                    "elementos": [
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá Lucas! Gostaria de um orçamento para ensaio fotográfico.",
                                                "texto": "Solicitar Orçamento no WhatsApp",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "redes_sociais",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "rede": "instagram",
                                                        "url": "https://instagram.com/perfil",
                                                    },
                                                    {
                                                        "rede": "youtube",
                                                        "url": "https://youtube.com/@perfil",
                                                    },
                                                ],
                                                "formato": "icones",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 8. Restaurante / Comércio
    # -------------------------------------------------------------------------
    {
        "nome": "Restaurante & Comércio",
        "slug": "restaurante-comercio",
        "categoria": "restaurante",
        "descricao": "Perfeito para restaurantes, cafeterias, hamburguerias, clínicas de estética e lojas locais divulgarem cardápio, horários e pedidos.",
        "ordem": 80,
        "estrutura_snapshot": {
            "schema_version": 1,
            "configuracao_visual": {
                "cor_primaria": "#dc2626",
                "cor_secundaria": "#f97316",
                "cor_fundo": "#ffffff",
                "cor_superficie": "#fef2f2",
                "cor_texto": "#1c1917",
                "cor_texto_secundario": "#78716c",
                "fonte_principal": "Poppins, sans-serif",
                "fonte_titulos": "Poppins, sans-serif",
                "radius_padrao": "16px",
                "sombra_padrao": "suave",
                "largura_maxima_mobile": 390,
            },
            "paginas": [
                {
                    "titulo": "Início",
                    "slug": "inicio",
                    "eh_inicial": True,
                    "secoes": [
                        {
                            "nome_interno": "Marca & Boas-vindas",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 24, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"alinhamento": "center"}},
                                    "elementos": [
                                        {
                                            "tipo": "avatar",
                                            "conteudo": {
                                                "url": "",
                                                "alt": "Logotipo Gastronomia",
                                                "forma": "circulo",
                                                "tamanho": 100,
                                                "borda": True,
                                            },
                                        },
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Bistrô San Marco",
                                                "nivel": "h1",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 24,
                                                    "peso_fonte": "700",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Cozinha Artesanal Italiana & Vinhos Selecionados"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 14,
                                                    "cor_texto": "#dc2626",
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "texto",
                                            "conteudo": {
                                                "texto": "Terça a Domingo: 12h às 15h e 19h às 23h30"
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 13,
                                                    "cor_texto": "#78716c",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Destaques do Cardápio",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 16}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {}},
                                    "elementos": [
                                        {
                                            "tipo": "titulo",
                                            "conteudo": {
                                                "texto": "Pratos Especiais do Chef",
                                                "nivel": "h3",
                                            },
                                            "estilos": {
                                                "base": {
                                                    "tamanho_fonte": 18,
                                                    "peso_fonte": "600",
                                                    "alinhamento": "center",
                                                }
                                            },
                                        },
                                        {
                                            "tipo": "servicos",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "titulo": "Tagliatelle al Tartufo",
                                                        "descricao": "Massa fresca artesanal com trufas negras e queijo parmigiano reggiano.",
                                                        "preco": "R$ 78",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Pedir no WhatsApp",
                                                    },
                                                    {
                                                        "titulo": "Risotto ai Frutti di Mare",
                                                        "descricao": "Arroz carnaroli com camarões, lulas e toque de vinho branco e açafrão.",
                                                        "preco": "R$ 89",
                                                        "link_cta": "https://wa.me/5511999999999",
                                                        "texto_cta": "Pedir no WhatsApp",
                                                    },
                                                ],
                                                "layout": "cards",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "nome_interno": "Pedidos & Como Chegar",
                            "tipo": "normal",
                            "estilos": {"base": {"padding_topo": 8, "padding_baixo": 24}},
                            "containers": [
                                {
                                    "tipo_layout": "stack",
                                    "estilos": {"base": {"gap": 10}},
                                    "elementos": [
                                        {
                                            "tipo": "whatsapp",
                                            "conteudo": {
                                                "numero": "5511999999999",
                                                "mensagem": "Olá! Gostaria de reservar uma mesa ou fazer um pedido.",
                                                "texto": "Fazer Pedido ou Reserva no WhatsApp",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "mapa",
                                            "conteudo": {
                                                "endereco": "Rua dos Pinheiros, 800 - Pinheiros, São Paulo - SP",
                                                "texto": "Como Chegar ao Restaurante",
                                                "largura_total": True,
                                            },
                                        },
                                        {
                                            "tipo": "redes_sociais",
                                            "conteudo": {
                                                "itens": [
                                                    {
                                                        "rede": "instagram",
                                                        "url": "https://instagram.com/perfil",
                                                    }
                                                ],
                                                "formato": "icones",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    },
]


# =============================================================================
# 15 BLOCOS REUTILIZÁVEIS DO SISTEMA
# =============================================================================

BLOCOS_SISTEMA: list[dict[str, Any]] = [
    # 1. Hero Minimal
    {
        "nome": "Hero Minimal",
        "slug": "hero-minimal",
        "categoria": "hero",
        "descricao": "Apresentação limpa com avatar circular, nome e descrição sucinta.",
        "ordem": 10,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Hero Minimal",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 24, "padding_baixo": 16}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"alinhamento": "center"}},
                        "elementos": [
                            {
                                "tipo": "avatar",
                                "conteudo": {
                                    "url": "",
                                    "alt": "Avatar",
                                    "forma": "circulo",
                                    "tamanho": 100,
                                    "borda": True,
                                },
                            },
                            {
                                "tipo": "titulo",
                                "conteudo": {"texto": "Seu Nome Completo", "nivel": "h1"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 24,
                                        "peso_fonte": "700",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "texto",
                                "conteudo": {
                                    "texto": "Sua Profissão | Uma breve descrição sobre seus serviços e diferenciais."
                                },
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 14,
                                        "cor_texto": "#64748b",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 2. Hero Foto
    {
        "nome": "Hero com Banner",
        "slug": "hero-banner",
        "categoria": "hero",
        "descricao": "Imagem de destaque com título forte e chamada para ação.",
        "ordem": 20,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Hero com Banner",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 20, "padding_baixo": 20}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"alinhamento": "center", "gap": 12}},
                        "elementos": [
                            {
                                "tipo": "imagem",
                                "conteudo": {
                                    "url": "",
                                    "alt": "Imagem de Destaque",
                                    "largura_total": True,
                                },
                            },
                            {
                                "tipo": "titulo",
                                "conteudo": {
                                    "texto": "Transforme sua Visão em Realidade",
                                    "nivel": "h2",
                                },
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 22,
                                        "peso_fonte": "700",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "botao",
                                "conteudo": {
                                    "texto": "Saiba Mais",
                                    "url": "https://meubiosite.com.br",
                                    "largura_total": True,
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 3. Hero Escuro
    {
        "nome": "Hero Escuro Glow",
        "slug": "hero-escuro",
        "categoria": "hero",
        "descricao": "Visual escuro elegante com contraste refinado.",
        "ordem": 30,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Hero Escuro",
                "tipo": "normal",
                "estilos": {
                    "base": {
                        "cor_fundo": "#0b0f19",
                        "cor_texto": "#f8fafc",
                        "padding_topo": 28,
                        "padding_baixo": 20,
                    }
                },
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"alinhamento": "center"}},
                        "elementos": [
                            {
                                "tipo": "avatar",
                                "conteudo": {
                                    "url": "",
                                    "alt": "Perfil",
                                    "forma": "circulo",
                                    "tamanho": 110,
                                    "borda": True,
                                },
                            },
                            {
                                "tipo": "titulo",
                                "conteudo": {"texto": "Presença Digital VIP", "nivel": "h1"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 26,
                                        "peso_fonte": "700",
                                        "cor_texto": "#f8fafc",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "texto",
                                "conteudo": {"texto": "Design Premium & Conversão Mobile"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 14,
                                        "cor_texto": "#38bdf8",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 4. Perfil Central
    {
        "nome": "Perfil Central",
        "slug": "perfil-central",
        "categoria": "perfil",
        "descricao": "Card de identidade com foto, nome e especialidade.",
        "ordem": 40,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Perfil Central",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 20, "padding_baixo": 16}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"alinhamento": "center", "gap": 8}},
                        "elementos": [
                            {
                                "tipo": "avatar",
                                "conteudo": {
                                    "url": "",
                                    "alt": "Perfil",
                                    "forma": "arredondado",
                                    "tamanho": 90,
                                    "borda": True,
                                },
                            },
                            {
                                "tipo": "titulo",
                                "conteudo": {"texto": "Seu Nome", "nivel": "h2"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 22,
                                        "peso_fonte": "700",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "texto",
                                "conteudo": {"texto": "Especialista em Resultados"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 14,
                                        "peso_fonte": "600",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 5. CTA WhatsApp
    {
        "nome": "CTA WhatsApp",
        "slug": "cta-whatsapp",
        "categoria": "cta",
        "descricao": "Botão em destaque para contato imediato no WhatsApp.",
        "ordem": 50,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "CTA WhatsApp",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 12, "padding_baixo": 12}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "whatsapp",
                                "conteudo": {
                                    "numero": "5511999999999",
                                    "mensagem": "Olá! Gostaria de atendimento.",
                                    "texto": "Falar no WhatsApp",
                                    "largura_total": True,
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 6. Links Rápidos
    {
        "nome": "Links Rápidos",
        "slug": "links-rapidos",
        "categoria": "links",
        "descricao": "Lista vertical de botões para websites, catálogos e canais.",
        "ordem": 60,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Links Rápidos",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 12, "padding_baixo": 12}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"gap": 10}},
                        "elementos": [
                            {
                                "tipo": "website",
                                "conteudo": {
                                    "url": "https://meubiosite.com.br",
                                    "texto": "Visitar Nosso Site Oficial",
                                    "largura_total": True,
                                },
                            },
                            {
                                "tipo": "botao",
                                "conteudo": {
                                    "texto": "Conhecer Nossos Cursos",
                                    "url": "https://meubiosite.com.br",
                                    "largura_total": True,
                                },
                            },
                            {
                                "tipo": "botao",
                                "conteudo": {
                                    "texto": "Baixar E-book Gratuito",
                                    "url": "https://meubiosite.com.br",
                                    "largura_total": True,
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 7. Redes Sociais
    {
        "nome": "Barra de Redes Sociais",
        "slug": "barra-redes-sociais",
        "categoria": "contato",
        "descricao": "Ícones organizados para Instagram, YouTube, LinkedIn, X e WhatsApp.",
        "ordem": 70,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Redes Sociais",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 10, "padding_baixo": 10}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"alinhamento": "center"}},
                        "elementos": [
                            {
                                "tipo": "redes_sociais",
                                "conteudo": {
                                    "itens": [
                                        {
                                            "rede": "instagram",
                                            "url": "https://instagram.com/perfil",
                                        },
                                        {"rede": "youtube", "url": "https://youtube.com/@perfil"},
                                        {
                                            "rede": "linkedin",
                                            "url": "https://linkedin.com/in/perfil",
                                        },
                                        {"rede": "whatsapp", "url": "https://wa.me/5511999999999"},
                                    ],
                                    "formato": "icones",
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 8. Serviços Cards
    {
        "nome": "Serviços em Cards",
        "slug": "servicos-cards",
        "categoria": "servicos",
        "descricao": "Cards elegantes de serviços com descrição, preço e botão de contratação.",
        "ordem": 80,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Serviços em Cards",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 16, "padding_baixo": 16}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "titulo",
                                "conteudo": {"texto": "Nossos Serviços", "nivel": "h3"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 20,
                                        "peso_fonte": "700",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "servicos",
                                "conteudo": {
                                    "itens": [
                                        {
                                            "titulo": "Consultoria Individual",
                                            "descricao": "Sessão dedicada de 1 hora com diagnóstico e plano prático.",
                                            "preco": "R$ 350",
                                            "link_cta": "https://wa.me/5511999999999",
                                            "texto_cta": "Contratar",
                                        },
                                        {
                                            "titulo": "Pacote Completo",
                                            "descricao": "Assessoria mensal com acompanhamento contínuo e suporte.",
                                            "preco": "R$ 980",
                                            "link_cta": "https://wa.me/5511999999999",
                                            "texto_cta": "Contratar",
                                        },
                                    ],
                                    "layout": "cards",
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 9. Serviços Compactos
    {
        "nome": "Serviços Compactos",
        "slug": "servicos-compactos",
        "categoria": "servicos",
        "descricao": "Lista enxuta com título, valor e chamada rápida.",
        "ordem": 90,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Serviços Compactos",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 12, "padding_baixo": 12}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "servicos",
                                "conteudo": {
                                    "itens": [
                                        {
                                            "titulo": "Atendimento Avulso",
                                            "descricao": "Sessão pontual.",
                                            "preco": "R$ 200",
                                            "link_cta": "https://wa.me/5511999999999",
                                            "texto_cta": "Agendar",
                                        }
                                    ],
                                    "layout": "compacto",
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 10. Galeria Grid
    {
        "nome": "Galeria em Grade",
        "slug": "galeria-grid",
        "categoria": "galeria",
        "descricao": "Grade de fotos com proporção quadrada perfeita para mobile.",
        "ordem": 100,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Galeria em Grade",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 14, "padding_baixo": 14}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "titulo",
                                "conteudo": {"texto": "Galeria de Imagens", "nivel": "h3"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 18,
                                        "peso_fonte": "600",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "galeria",
                                "conteudo": {
                                    "layout": "grid",
                                    "colunas": 2,
                                    "imagens": [
                                        {"url": "", "alt": "Foto 1"},
                                        {"url": "", "alt": "Foto 2"},
                                        {"url": "", "alt": "Foto 3"},
                                        {"url": "", "alt": "Foto 4"},
                                    ],
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 11. Galeria Horizontal
    {
        "nome": "Galeria Horizontal (Carrossel)",
        "slug": "galeria-horizontal",
        "categoria": "galeria",
        "descricao": "Carrossel de imagens com scroll horizontal e suporte a toque/swipe.",
        "ordem": 110,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Galeria Horizontal",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 14, "padding_baixo": 14}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "titulo",
                                "conteudo": {"texto": "Destaques Recentes", "nivel": "h3"},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 18,
                                        "peso_fonte": "600",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                            {
                                "tipo": "galeria",
                                "conteudo": {
                                    "layout": "carrossel",
                                    "imagens": [
                                        {"url": "", "alt": "Slide 1"},
                                        {"url": "", "alt": "Slide 2"},
                                        {"url": "", "alt": "Slide 3"},
                                    ],
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 12. Agendamento
    {
        "nome": "Agendamento Externo",
        "slug": "agendamento-externo",
        "categoria": "servicos",
        "descricao": "Botão de reserva de horários online com calendário.",
        "ordem": 120,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Agendamento Online",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 12, "padding_baixo": 12}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "agendamento_externo",
                                "conteudo": {
                                    "url": "https://calendar.google.com/",
                                    "texto": "📅 Agendar Horário Disponível",
                                    "largura_total": True,
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 13. Localização
    {
        "nome": "Localização / Mapa",
        "slug": "localizacao-mapa",
        "categoria": "localizacao",
        "descricao": "Botão com endereço formatado e rota no Google Maps.",
        "ordem": 130,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Localização",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 12, "padding_baixo": 12}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {}},
                        "elementos": [
                            {
                                "tipo": "mapa",
                                "conteudo": {
                                    "endereco": "Av. Paulista, 1000 - São Paulo, SP",
                                    "texto": "📍 Ver Endereço no Google Maps",
                                    "largura_total": True,
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 14. Contato Direto
    {
        "nome": "Contato Direto",
        "slug": "contato-direto",
        "categoria": "contato",
        "descricao": "Ações rápidas de ligação telefônica e e-mail.",
        "ordem": 140,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Contato Direto",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 12, "padding_baixo": 12}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"gap": 10}},
                        "elementos": [
                            {
                                "tipo": "telefone",
                                "conteudo": {
                                    "numero": "(11) 99999-9999",
                                    "texto": "Ligar no Telefone",
                                    "largura_total": True,
                                },
                            },
                            {
                                "tipo": "email",
                                "conteudo": {
                                    "email": "contato@meubiosite.com",
                                    "texto": "Enviar Mensagem por E-mail",
                                    "assunto": "Contato BioSite",
                                    "largura_total": True,
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
    # 15. Rodapé Minimal
    {
        "nome": "Rodapé Minimalista",
        "slug": "rodape-minimal",
        "categoria": "rodape",
        "descricao": "Divisor discreto com copyright e ano corrente.",
        "ordem": 150,
        "estrutura_snapshot": {
            "schema_version": 1,
            "secao": {
                "nome_interno": "Rodapé",
                "tipo": "normal",
                "estilos": {"base": {"padding_topo": 20, "padding_baixo": 24}},
                "containers": [
                    {
                        "tipo_layout": "stack",
                        "estilos": {"base": {"alinhamento": "center"}},
                        "elementos": [
                            {
                                "tipo": "divisor",
                                "conteudo": {
                                    "estilo": "solid",
                                    "espessura": 1,
                                    "largura": "60%",
                                    "espacamento": 16,
                                },
                            },
                            {
                                "tipo": "texto",
                                "conteudo": {"texto": "© 2026 Todos os direitos reservados."},
                                "estilos": {
                                    "base": {
                                        "tamanho_fonte": 12,
                                        "cor_texto": "#94a3b8",
                                        "alinhamento": "center",
                                    }
                                },
                            },
                        ],
                    }
                ],
            },
        },
    },
]
