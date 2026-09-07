# Plataforma Privada de BioSites com NFC — Django

Plataforma centralizada e modular para criação, gerenciamento, publicação e hospedagem de múltiplos BioSites com suporte a tags NFC, QR Code e URLs amigáveis.

---

## 1. Projeto e Objetivo

O objetivo desta plataforma é viabilizar que o proprietário/administrador do sistema crie e gerencie BioSites modernos para clientes comerciais, permitindo que visitantes acessem os perfis por meio de:
- Aproximação física de cartões/tags **NFC**;
- Leitura de **QR Code**;
- URLs amigáveis na web (com suporte futuro a subdomínios e domínios próprios).

O sistema é construído sob a premissa de:
```text
UMA APLICAÇÃO DJANGO
+
UM BANCO CENTRAL
+
UM PAINEL ADMINISTRATIVO PRIVADO
+
VÁRIOS BIOSITES PÚBLICOS
```

> **Aviso Importante:** Clientes comerciais e visitantes **não** possuem conta de usuário no sistema Django. Apenas a equipe administrativa interna possui credenciais de acesso.

---

## 2. Princípio Arquitetural: Monólito Modular Django

Adotamos a arquitetura de **Monólito Modular** utilizando os recursos nativos de excelência do Django. Essa decisão proporciona:
- **Simplicidade Operacional:** Deploy único, sem overhead de orquestração distribuída ou microserviços prematuros;
- **Modularidade e Baixo Acoplamento:** Divisão estrita de responsabilidades por domínios em aplicativos isolados (`core`, `administracao`, e futuros apps);
- **Segurança de Alto Nível:** Proteção nativa contra CSRF, XSS, Clickjacking, injeção de SQL e gestão segura de sessões;
- **Escalabilidade Vertical e Horizontal Previsível:** Modelo centralizado que suporta de dezenas a dezenas de milhares de BioSites com performance relacional otimizada.

---

## 3. Stack Tecnológica Selecionada

```text
Versão Python escolhida: Python 3.12 (Python 3.12.10)
Versão Django escolhida: Django 5.2 LTS (5.2.x)
Motivo técnico da escolha:
- Python 3.12 oferece o equilíbrio perfeito entre máxima estabilidade em ambientes de produção, suporte de longo prazo ativo e 100% de disponibilidade de pacotes binários (wheels) compilados para C-extensions críticas no Windows e Linux (como psycopg, criptografia e manipulação de imagem). Evita instabilidades e ausência de wheels encontradas em versões de pré-lançamento como Python 3.14.
- Django 5.2 é a versão LTS (Long Term Support) atual, assegurando suporte a patches de segurança e manutenção estendida por pelo menos 3 anos. Traz melhorias substanciais no ORM, formulários, renderização assíncrona segura e validações de sessão, sem risco de breaking changes de versões intermediárias.
```

### Principais Dependências:
- **`django`** (`>=5.2,<5.3`): Framework web principal.
- **`django-environ`** (`>=0.12.0`): Gerenciamento de configurações segundo os princípios *12-Factor App*.
- **`psycopg[binary]`** (`>=3.2.0`): Driver PostgreSQL de alta performance e compatibilidade para produção.
- **`ruff`** (`>=0.9.0`): Linter e formatador de código Python ultrarrápido.

---

## 4. Estrutura de Diretórios

```text
biosite_nfc/
│
├── manage.py                   # Utilitário de linha de comando do Django
├── .env.example                # Template documentado de variáveis de ambiente
├── .env                        # Variáveis locais de desenvolvimento (ignorado no Git)
├── .gitignore                  # Arquivos e pastas ignorados pelo controle de versão
├── pyproject.toml              # Metadados do projeto e configurações do Ruff
├── README.md                   # Documentação arquitetural e guia de operação
│
├── requirements/
│   ├── base.txt                # Dependências compartilhadas (Django, django-environ)
│   ├── desenvolvimento.txt     # Dependências para ambiente local (ruff, psycopg)
│   └── producao.txt            # Dependências específicas para deploy de produção
│
├── configuracao/               # Módulo de orquestração do projeto
│   ├── __init__.py
│   ├── asgi.py                 # Ponto de entrada ASGI
│   ├── wsgi.py                 # Ponto de entrada WSGI
│   ├── urls.py                 # Roteamento global de URLs com namespaces
│   └── settings/
│       ├── __init__.py
│       ├── base.py             # Configurações compartilhadas entre todos os ambientes
│       ├── desenvolvimento.py  # Ambiente local (DEBUG=True, SQLite)
│       ├── teste.py            # Ambiente de testes automatizados (:memory:)
│       └── producao.py         # Ambiente de produção (DEBUG=False, PostgreSQL, HTTPS)
│
├── aplicativos/                # Domínios de negócio isolados
│   ├── __init__.py
│   ├── core/                   # Núcleo compartilhado, modelos base e health check
│   │   ├── apps.py
│   │   ├── models.py           # ModeloBase com ID interno, UUID público e timestamps
│   │   ├── views.py            # View de health check (/health/) e home temporária
│   │   ├── urls.py             # URLs públicas do core
│   │   ├── urls_health.py      # URL operacional de monitoramento
│   │   └── tests.py            # Testes de liveness, home e ModeloBase
│   │
│   └── administracao/          # Gestão e autenticação de usuários administrativos
│       ├── apps.py
│       ├── models.py           # UsuarioAdministrativo (Custom User Model)
│       ├── managers.py         # UsuarioAdministrativoManager com create_superuser
│       ├── admin.py            # Registro no Django Admin
│       ├── migrations/         # Migrations do usuário administrativo
│       └── tests.py            # Testes de criação, superusuário e integridade de senhas
│
├── templates/                  # Templates HTML organizados
│   ├── base.html               # Layout base corporativo
│   ├── 404.html                # Página de erro 404 customizada e segura
│   ├── 500.html                # Página de erro 500 customizada (sem vazamento de dados)
│   └── core/
│       └── index.html          # Página inicial indicando status operacional
│
├── static/                     # Arquivos estáticos coletados
│   ├── css/
│   │   └── style.css           # Estilos visuais fundamentais
│   ├── js/                     # Scripts globais
│   └── img/                    # Logos e imagens da plataforma
│
├── media/                      # Uploads de mídia (avatares, capas, logos futuros)
│
└── testes/                     # Testes de integração de ambiente e configurações
    ├── __init__.py
    └── test_settings.py        # Testes de integridade de settings e proteções de produção
```

---

## 5. Decisões Arquiteturais Iniciais

1. **Modelo de Usuário Customizado (`UsuarioAdministrativo`):**
   - Definido antes da primeira migration através de `AUTH_USER_MODEL = "administracao.UsuarioAdministrativo"`.
   - Extende `AbstractUser`, garantindo total compatibilidade com `is_staff`, `is_superuser`, grupos e permissões nativas.
   - O endereço de e-mail é único e obrigatório.
   - Segregação conceitual: usuários representam apenas administradores do sistema; clientes de BioSites não possuem contas de login.

2. **Estratégia de Identificadores (ID vs UUID):**
   - As entidades herdam de `ModeloBase` (`aplicativos/core/models.py`).
   - `id` (`BigAutoField`): Chave primária relacional sequencial interna para máximo desempenho em índices e chaves estrangeiras.
   - `uuid` (`UUIDField`): Identificador universal imutável e único, exposto publicamente em URLs, tags NFC e QR Codes, impedindo a enumeração maliciosa de IDs sequenciais.

3. **Separação de Ambientes de Configurações:**
   - Modularização estrita em `base.py`, `desenvolvimento.py`, `teste.py` e `producao.py`.
   - `producao.py` valida ativamente a presença de `DJANGO_SECRET_KEY` (impedindo chaves fracas ou padrão), `ALLOWED_HOSTS` e `DATABASE_URL`, lançando `ImproperlyConfigured` em caso de irregularidades.

4. **Banco de Dados (Desenvolvimento vs Produção):**
   - **Desenvolvimento:** Padrão SQLite local (`db.sqlite3`) para inicialização imediata e sem atrito.
   - **Produção:** PostgreSQL gerenciado via variável de ambiente `DATABASE_URL` no formato `postgres://usuario:senha@host:5432/nome_banco`, com suporte ao driver `psycopg` 3.

5. **Endpoint de Monitoramento Operacional (Health Check):**
   - Endpoint `/health/` respondendo com HTTP 200 e `{"status": "ok"}`.
   - Projetado para monitoramento de liveness por load balancers (AWS ALB, Cloudflare, Traefik, Docker healthcheck) sem expor versões de software, variáveis de ambiente ou topologia do servidor.

---

## 6. Instalação e Execução Passo a Passo

### Pré-requisitos
- Python 3.12 instalado
- Git configurado

### 1. Clonar o Repositório e Navegar até a Pasta
```bash
git clone https://github.com/AndrzzO/SITE_BIOSITE.git
cd SITE_BIOSITE
```

### 2. Criar e Ativar o Ambiente Virtual
No Windows (PowerShell):
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
No Linux / macOS:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements/desenvolvimento.txt
```

### 4. Configurar as Variáveis de Ambiente
Copie o arquivo de exemplo para `.env`:
```bash
cp .env.example .env
```
*(No Windows PowerShell: `Copy-Item .env.example .env`)*

### 5. Executar as Migrações
```bash
python manage.py migrate
```

### 6. Criar o Primeiro Usuário Administrador
```bash
python manage.py createsuperuser
```
Informe seu nome de usuário, e-mail administrativo e uma senha segura.

### 7. Executar Verificações do Sistema
```bash
python manage.py check
```

### 8. Executar a Suíte de Testes Automatizados
```bash
python manage.py test
```

### 9. Iniciar o Servidor de Desenvolvimento
```bash
python manage.py runserver
```
Acesse:
- **Página Inicial:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Painel Administrativo Privado:** [http://127.0.0.1:8000/painel/](http://127.0.0.1:8000/painel/)
- **Login Administrativo:** [http://127.0.0.1:8000/painel/login/](http://127.0.0.1:8000/painel/login/)
- **Health Check:** [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/)
- **Django Admin (Técnico):** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 7. Filosofia do Produto e Diretrizes de Design

### 7.1 Definição Oficial
Plataforma privada de criação, edição, publicação e hospedagem de sites em Django, com experiência estrutural inspirada no **Google Sites**, liberdade visual progressivamente inspirada no **Canva** e fluxo de projeto/preview/versão conceitualmente semelhante ao **Lovable**.

### 7.2 Regra de Uso Exclusivamente Privado
- O construtor **não é um SaaS aberto ao público**.
- Apenas a equipe interna/proprietário opera o painel administrativo.
- Clientes comerciais **não possuem login** nem contas no sistema. O cliente recebe e acessa apenas o BioSite final publicado.

### 7.3 Diferença Crucial: Editor vs. BioSite Publicado
```text
EDITOR (Painel Administrativo):
→ Ferramenta de trabalho interna
→ Otimizada para telas médias e grandes (Desktop / Tablet)
→ Prioridade: Clareza, velocidade, estabilidade e praticidade operacional

BIOSITE (Produto Comercial Final):
→ Prioridade absoluta: SMARTPHONE-FIRST
→ Viewport de referência primário: 390px de largura
→ Faixa prioritária de dispositivos: 320px a 430px (orientação portrait)
→ Compatibilidade com desktop tratada de forma secundária
```

---

## 8. Autenticação Administrativa e Workspace (Prompt 2)

### 8.1 Acesso e Credenciais
- **Acesso Privado:** `/painel/login/` (sem links de cadastro público ou criação de conta).
- **Identificação:** Suporta login via **Nome de Usuário** ou **E-mail**.
- **Mensagem Genérica de Erro:** Em caso de credenciais incorretas ou conta inativa, exibe unicamente *"Usuário ou senha inválidos."*, prevenindo enumeração de operadores.

### 8.2 Proteção de Acesso e Autorização
- **Camada Centralizada:** Toda a área privada é protegida por `RequerAutenticacaoAdministrativaMixin` e `@requer_autenticacao_administrativa`.
- **Condições Mandatórias:** Requer `is_authenticated=True`, `is_active=True` e `is_staff=True`. Usuários sem privilégio `is_staff` recebem HTTP 403 Forbidden.
- **Validação Anti-Open Redirect:** O parâmetro `next` é validado estritamente por `url_has_allowed_host_and_scheme` antes de qualquer redirecionamento.

### 8.3 Rate Limiting Contra Força Bruta
- Implementado via `ServicoRateLimitLogin` utilizando cache nativo do Django (`django.core.cache.cache`).
- Chaves geradas com base no IP do cliente e identificador informado.
- Política: 5 tentativas falhas dentro de 5 minutos bloqueiam temporariamente tentativas subsequentes por 10 minutos. Afeta estritamente o login, sem interromper outras navegações.

### 8.4 Sessões e Logout Seguro
- Duração da sessão administrativa configurada para 12 horas (`SESSION_COOKIE_AGE = 43200`).
- Flags `HttpOnly` e `SameSite=Lax` ativadas.
- Rota de logout `/painel/logout/` executada preferencialmente via requisição `POST` com token CSRF, encerrando a sessão e redirecionando ao login.

### 8.5 Workspace "Meus Sites"
- Rota: `/painel/sites/` (com redirecionamento automático a partir de `/painel/`).
- Layout estruturado no padrão Google Sites / Canva, exibindo cards reais, busca no backend, filtros por status e paginação.

---

## 9. Clientes, Projetos de Site e Workspace Funcional (Prompt 3)

### 9.1 Modelo `Cliente` (`aplicativos/clientes/`)
- Representa a entidade comercial compradora ou beneficiária dos sites.
- **Não é usuário do Django:** não possui credenciais, nem acesso ao painel de administração.
- **Campos:** `nome` (*único campo obrigatório*), `nome_fantasia`, `email`, `telefone`, `whatsapp`, `documento` (CPF/CNPJ opcional), `observacoes`, `status` (`ATIVO` / `ARQUIVADO`) e `arquivado_em`.
- **Integridade:** Exclusão protegida (`PROTECT`) — clientes com projetos vinculados não podem ser deletados acidentalmente via cascata.
- **CRUD Completo:** Listagem paginada (`/painel/clientes/`), cadastro com atalho para novo site (`/painel/clientes/novo/`), página de detalhes com lista de projetos associados e botão de arquivamento/restauração via `POST`.

### 9.2 Modelo `ProjetoSite` (`aplicativos/sites/`)
- Objeto central do construtor de sites e BioSites.
- **Campos:** `cliente` (FK obrigatória com `PROTECT`), `nome`, `slug` (único, validado contra palavras reservadas), `tipo` (`BIOSITE` por padrão, `LANDING_PAGE`, `SITE`, `PORTFOLIO`, `CARDAPIO`, `OUTRO`), `status` (`RASCUNHO` por padrão, `PUBLICADO`, `ARQUIVADO`, `SUSPENSO`), `descricao_interna`, `thumbnail` (com fallback neutro) e `arquivado_em`.
- **Sem Funcionalidades Falsas:** O status `PUBLICADO` existe no enum, mas a interface não permite publicar diretamente sem o motor de compilação/publicação real (previsto para etapas posteriores).

### 9.3 Serviços de Domínio (`aplicativos/sites/servicos.py`)
- **Geração e Normalização de Slugs:** Gera slugs a partir do nome via `slugify`, resolve colisões sequenciais (`-2`, `-3`) e impede palavras reservadas (`admin`, `painel`, `login`, `static`, etc.).
- **Duplicação Atômica de Projetos:** Executa `duplicar_projeto()` dentro de `transaction.atomic()`, copiando cliente, tipo e notas com novo ID, novo UUID, novo slug derivado (`-copia`), timestamps renovados e status forçado para `RASCUNHO`.

### 9.4 Decisão de Banco de Dados: SQLite na Fase Atual
- O SQLite local (`db.sqlite3`) é utilizado nesta etapa por simplicidade, agilidade e ausência de concorrência (ferramenta de operador único).
- A arquitetura dos models é 100% portável e pronta para PostgreSQL via `DATABASE_URL` quando a escala do produto exigir.

### 9.5 Decisão sobre Agendamentos
- A plataforma **não implementa sistema próprio de agendamento/calendário** no banco.
- O futuro componente de agendamento nos BioSites integrará diretamente com serviços consolidados de terceiros, com o **Google Agenda** como primeira opção via link externo.

---

## 10. Motor Estrutural de Páginas, Seções, Containers e Elementos (Prompt 4)

A arquitetura do construtor de BioSites estrutura cada projeto em entidades relacionais reais no banco de dados:
```text
Cliente ──> ProjetoSite ──> PaginaSite ──> SecaoSite ──> ContainerSite ──> ElementoSite
```

### 10.1 Modelos Estruturais (`aplicativos/sites/models.py`)
- **`PaginaSite`:** Representa páginas do site. Possui restrição de unicidade para o slug dentro do projeto (`unique_pagina_slug_por_projeto`) e restrição de página inicial única por projeto (`unique_pagina_inicial_por_projeto`).
- **`SecaoSite`:** Divisão vertical da página (`NORMAL`, `ALTURA_MINIMA`, `TELA_CHEIA`).
- **`ContainerSite`:** Gerenciador de layout (`STACK`, `ROW`, `GRID`, `OVERLAY`) com suporte a aninhamento seguro de até 3 níveis de profundidade, validação de ciclos e proibição de parentes em seções diferentes.
- **`ElementoSite`:** Unidade atômica de conteúdo. Utiliza `conteudo` (JSONField validado pelo schema do tipo) e `estilos` (JSONField com allowlist mobile-first: `{"base": {...}, "desktop": {...}}`).

### 10.2 Registry Extensível e Desacoplado (`aplicativos/sites/elementos/`)
- Singleton `RegistroElementos` elimina blocos condicionais monolíticos.
- Definições implementadas: `TITULO`, `TEXTO`, `BOTAO`, `IMAGEM`, `ESPACADOR`, `ICONE`.
- Sanitização automática contra XSS (`escape`) e bloqueio estrito de protocolos inseguros (`javascript:`, `data:`).

### 10.3 Serviços de Domínio e Duplicação Profunda (`aplicativos/sites/servicos_estrutura.py`)
- **Criação Idempotente de Página Inicial:** `garantir_pagina_inicial(projeto)` garante que todo projeto possua a página `Início` com seção e container padrão.
- **Reordenação Atômica:** `reordenar_entidades()` utiliza passos de 10 validando parentesco.
- **Duplicação Profunda:** `duplicar_elemento()`, `duplicar_secao()`, `duplicar_pagina()` e `duplicar_projeto_completo()` clonam recursivamente toda a árvore estrutural com novos IDs, UUIDs, timestamps e status forçado para `RASCUNHO`.
- **Serialização Otimizada:** `obter_estrutura_projeto()` executa apenas 5 queries fixas com prefetch aninhado, eliminando completamente o problema N+1.
- **Auditoria de Integridade:** `auditar_integridade_projeto()` detecta anomalias como ausência de página inicial ou cruzamento de seções.

---

## 11. Qualidade de Código e Lint

Para verificar conformidade com a PEP 8:
```bash
ruff check .
```

Para formatar automaticamente o código:
```bash
ruff format .
```

---

## 12. Próximas Etapas (Prompts 5 a 12)

1. **Prompt 1:** Fundação, Arquitetura e Configuração do Projeto *(Concluído)*
2. **Prompt 2:** Autenticação Privada e Workspace "Meus Sites" *(Concluído)*
3. **Prompt 3:** Clientes, Projetos de Site e Workspace "Meus Sites" Funcional *(Concluído)*
4. **Prompt 4:** Motor Estrutural de Páginas, Seções, Containers e Elementos *(Concluído)*
5. **Prompt 5:** Editor Visual Mobile-First
6. **Prompt 6:** Componentes e Blocos Específicos de BioSite
7. **Prompt 7:** Temas, Tipografia e Design System
8. **Prompt 8:** Integração e Redirecionamento NFC
9. **Prompt 9:** QR Code Dinâmico e Exportação
10. **Prompt 10:** Analytics e Telemetria de Visitas
11. **Prompt 11:** Hardening, Performance e Preparação para Produção
12. **Prompt 12:** Auditoria e Testes Finais

