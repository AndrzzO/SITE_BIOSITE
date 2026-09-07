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
- **Health Check:** [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/)
- **Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 7. Qualidade de Código e Lint

Para verificar o padrão de código e conformidade com a PEP 8:
```bash
ruff check .
```

Para formatar automaticamente o código:
```bash
ruff format .
```

---

## 8. Próximas Etapas (Prompts 2 a 12)

Esta base servirá de fundação fixa para as próximas entregas sequenciais:
1. **Prompt 2:** Autenticação e Painel Administrativo Privado
2. **Prompt 3:** Clientes
3. **Prompt 4:** BioSites
4. **Prompt 5:** Componentes dos BioSites
5. **Prompt 6:** Editor Visual
6. **Prompt 7:** Temas e Design System
7. **Prompt 8:** Integração e Redirecionamento NFC
8. **Prompt 9:** QR Code
9. **Prompt 10:** Analytics e Telemetria
10. **Prompt 11:** Hardening, Performance e Preparação para Produção
11. **Prompt 12:** Auditoria e Testes Finais
