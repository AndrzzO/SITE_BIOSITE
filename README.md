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

## 11. Editor Visual Mobile-First e Preview (Prompt 5)

O estúdio de edição visual combina a simplicidade estrutural do **Google Sites** com a manipulação visual fluida e intuitiva inspirada no **Canva**, priorizando a filosofia **Smartphone-First** em todo o ciclo de vida.

### 11.1 Arquitetura do Estúdio (`/painel/sites/<uuid>/editor/`)
- **Smartphone-First Nativo:** O canvas de trabalho abre por padrão com largura de **390px** (proporção 390×844 baseada no iPhone 12/13/14), com seletor instantâneo de viewports na barra inferior:
  - **320px** (Telas compactas)
  - **360px** (Android padrão)
  - **375px** (iPhone clássico)
  - **390px** (Padrão de referência)
  - **412px** (Android moderno)
  - **430px** (Max/Plus)
  - **Desktop (100%)**
- **Renderização em DOM Direto com Isolamento CSS:** O canvas de edição e o preview operam no mesmo documento DOM com estrito isolamento por namespaces (`#editor-studio-app` para a interface do estúdio vs `#biosite-canvas-viewport` e `.biosite-canvas-root` para o conteúdo do BioSite), evitando as complexidades e atritos de sincronização de iframes.
- **Motor de Renderização Compartilhado (`aplicativos/sites/renderer.py`):** A classe universal `RenderizadorBioSite` gera HTML semântico com injeção de CSS mobile-first (`.biosite-elem-<id>`, `.biosite-sec-<id>`) e media queries para desktop (`@media (min-width: 768px)`), alternando entre modo administrativo (`modo="editor"`) e modo limpo (`modo="preview"`).

### 11.2 Interações Visuais e Drag-and-Drop
- **SortableJS Local:** Utiliza `SortableJS` (v1.15.6) empacotado localmente (`static/editor/js/vendor/sortable.min.js`), com zero dependência de CDNs externas.
- **Reordenação de Seções:** Arraste vertical de seções via alça (`⋮⋮`) com persistência imediata no backend.
- **Manipulação de Elementos:** Arraste e solte de elementos dentro do mesmo container ou transferência fluida entre containers diferentes.
- **Paleta de Elementos:** Inserção imediata por clique na barra lateral esquerda ou por arrastar para o container desejado.
- **Edição de Texto in loco (Inline):** Duplo clique em títulos (`TITULO`) ou parágrafos (`TEXTO`) ativa edição instantânea (`contenteditable`), com sanitização rigorosa de colar (`paste`) em texto puro sem formatação externa indesejada.

### 11.3 Painel de Propriedades e Autosave
- **Inspetor Contextual (Sidebar Direita):** Ao selecionar um elemento, container ou seção, o painel exibe seus parâmetros de conteúdo (texto, nível h1-h6, rótulo, URL de link) e controles de estilo:
  - Edição base (Mobile-first)
  - Overrides específicos para Desktop
  - Cores, tipografia, alinhamento, espaçamentos e bordas
- **Debounced Autosave (700ms):** Fila de salvamento assíncrono com indicador visual na barra superior (`Salvando...`, `✓ Salvo`, `Erro ao salvar`) e proteção contra fechamento acidental de aba (`beforeunload`).
- **Histórico e Teclas de Atalho:** Pilha de Undo/Redo na sessão do navegador com suporte completo a atalhos:
  - `Ctrl + S`: Força salvamento manual imediato
  - `Ctrl + Z`: Desfazer
  - `Ctrl + Y` / `Ctrl + Shift + Z`: Refazer
  - `Ctrl + D`: Duplicar entidade selecionada
  - `Delete` / `Backspace`: Excluir entidade selecionada
  - `Esc`: Limpar seleção ativa

### 11.4 Visualização Fiel e Segura (Preview)
- **Rota Dedicada:** `/painel/sites/<uuid>/preview/` exibe o rascunho com 100% de paridade visual em relação ao editor, renderizado com `RenderizadorBioSite(modo="preview")` sem qualquer alça, toolbar ou wrapper administrativo.
- **Proteção IDOR Estrita:** Todas as rotas de API do editor validam a integridade de projeto cruzado no nível mais profundo (`elemento.container.secao.pagina.projeto == site`), retornando 404/422 diante de qualquer tentativa de adulteração de nós.
- **Botão de Publicação Informativo:** Botão "Publicar" explicitamente desativado com indicação visual para o Prompt 11, evitando simulação ou falsas publicações.

---

---

## 12. Design System, Propriedades Visuais Avançadas e Componentes Premium (Prompt 6)

O Prompt 6 eleva a plataforma de um editor funcional básico para um patamar de **qualidade visual comercial premium**, assegurando consistência estética, responsividade refinada e componentes especializados para BioSites profissionais.

### 12.1 Design Tokens e CSS Custom Properties
- **ConfiguracaoVisualProjeto:** Modelo acoplado 1:1 a cada `ProjetoSite`, armazenando tokens globais de identidade visual:
  - Cores: `--cor-primaria`, `--cor-secundaria`, `--cor-fundo`, `--cor-superficie`, `--cor-texto`, `--cor-texto-secundario`
  - Tipografia: `--fonte-principal` e `--fonte-titulos` (Inter, Roboto, Plus Jakarta Sans, Poppins, Playfair Display, Montserrat, etc.)
  - Geometria e Elevação: `--radius-padrao` (0px a 9999px) e `--sombra-padrao` (nenhuma, suave, media, forte, glow)
  - Largura Máxima Mobile: `--largura-maxima-mobile` (padrão 390px)
- **Injeção de Tokens CSS (`aplicativos/sites/renderer.py`):** Tanto o canvas do estúdio quanto a rota de preview recebem um bloco `<style id="biosite-tokens-css">` gerado por `gerar_bloco_css()`, aplicando variáveis sobre `:root, .biosite-canvas-root` para paridade visual rigorosa.

### 12.2 Herança de Estilos e Presets de Design
- **Hierarquia de Estilos:** Projeto (Global) &rarr; Seção &rarr; Container &rarr; Elemento.
- **Botão "Usar padrão do projeto":** Em cada propriedade no inspetor lateral (cores, bordas, sombras, fontes), campos vazios herdam dinamicamente as variáveis CSS correspondentes, permitindo reset instantâneo.
- **Temas & Presets Rápidos:** 5 combinações prontas para aplicação em um clique no estúdio: Clean Light, Dark Premium, Modern Violet, Warm Elegance e Minimalist Gray.
- **Verificação de Contraste WCAG 2.1:** Algoritmo matemático integrado que analisa em tempo real o contraste entre texto e fundo (`(L1 + 0.05) / (L2 + 0.05)`), exibindo badges informativos no painel sem bloquear a criatividade do usuário.

### 12.3 Catálogo Expandido de Componentes Premium
O registro centralizado (`aplicativos/sites/elementos/`) foi ampliado com componentes específicos para alta conversão mobile:
- **WhatsApp (`WHATSAPP`):** Normalização automática de números telefônicos para formato internacional, geração de link seguro `https://wa.me/<numero>?text=<mensagem>` e suporte a botão fixo flutuante (`cta_flutuante`).
- **Telefone (`TELEFONE`):** Botão formatado com ação nativa `tel:<numero>`.
- **E-mail (`EMAIL`):** Botão com validação de formato e geração de link `mailto:<email>?subject=<assunto>`.
- **Website / Link Externo (`WEBSITE`):** Botão de link com suporte a rótulo, URL e segurança `rel="noopener noreferrer"`.
- **Redes Sociais (`REDES_SOCIAIS`):** Barra multicanal suportando Instagram, Facebook, TikTok, LinkedIn, YouTube, Twitter/X e WhatsApp em modos ícones ou botões completos.
- **Agendamento Externo (`AGENDAMENTO_EXTERNO`):** Botão com destaque visual e integração com Google Agenda, Calendly ou URLs customizadas.
- **Localização / Mapa (`MAPA`):** Link direto para pesquisa de endereço no Google Maps (`https://www.google.com/maps/search/?api=1&query=...`), sem custos de APIs pagas.
- **Lista de Serviços (`SERVICOS`):** Cards de apresentação de serviços e produtos com título, descrição, badge de preço e botão CTA dedicado.
- **Galeria de Fotos (`GALERIA`):** Layouts em grade responsiva (1 a 4 colunas) ou carrossel horizontal com suporte nativo a touch/swipe (`scroll-snap`).
- **Avatar de Perfil (`AVATAR`):** Foto de perfil ou logotipo em formas circular, arredondada ou quadrada, com bordas configuráveis e suporte a placeholder SVG.
- **Divisor Horizontal (`DIVISOR`):** Linhas de separação personalizadas (sólida, tracejada, pontilhada, dupla) com controle de espessura e largura.
- **Biblioteca Interna de Ícones SVG (`aplicativos/sites/elementos/icones.py`):** SVGs otimizados sem dependência de fontes de ícones externas.

### 12.4 Pipeline de Upload Seguro e Otimização de Mídia
- **Modelo `MidiaSite`:** Armazenamento centralizado de ativos de mídia por projeto (`upload_to="sites/midias/%Y/%m/"`), com rastreamento de dimensões, tamanho e tipo.
- **Sanitização com Pillow (`aplicativos/sites/servicos_midia.py`):**
  - Verificação real de bytes via `Image.open().verify()` contra executáveis disfarçados.
  - Bloqueio estrito de arquivos `.svg` em uploads de usuários para eliminar vetores de SVG-XSS.
  - Correção automática de rotação EXIF mobile via `ImageOps.exif_transpose()`.
  - Remoção completa de metadados sensíveis (geolocalização, dados de câmera).
  - Redimensionamento inteligente para telas mobile (máximo 1200px) e conversão automática para formato moderno **WebP** com compressão de alta qualidade.
  - Limite de 10 MB por upload e validação de isolamento por projeto (IDOR).

### 12.5 Animações e Movimento Suave
- Transições sutis (`fade`, `fade-up`, `scale`, `slide`) implementadas em CSS puro.
- Suporte total a acessibilidade motora com desativação automática via `@media (prefers-reduced-motion: reduce)`.

---

## 13. Templates, Blocos Reutilizáveis e Criação Rápida de BioSites (Prompt 7)

O Prompt 7 introduz um ecossistema completo de **Templates de Sites** e **Blocos Reutilizáveis** baseado em snapshots estruturais versionados em `JSONField`, acelerando a produção comercial de BioSites sem duplicar tabelas relacionais nem gerar acoplamentos em tempo de execução.

### 13.1 Arquitetura de Snapshots Versionados
- **Modelos de Blueprints:**
  - `TemplateSite`: Snapshot estrutural completo (`configuracao_visual` e árvore recursiva de `paginas`, `secoes`, `containers` e `elementos`).
  - `BlocoReutilizavel`: Snapshot de seção individual (`containers` e `elementos`).
- **Validação Rigorosa (`SCHEMA_VERSION = 1`):** Validador estrutural em `aplicativos/sites/validadores_templates.py` que audita integridade de chaves, existência dos elementos no catálogo de `RegistroElementos`, payloads e URLs perigosas (`javascript:`, etc.).
- **Clonagem Profunda Atômica (`servicos_templates.py`):**
  - `instanciar_template()` e `instanciar_bloco()` geram novas árvores com IDs e UUIDs próprios e status `RASCUNHO`.
  - Transações atômicas garantem rollback total caso ocorra qualquer inconsistência.
  - Independência total: mutações no projeto derivado não afetam o template e vice-versa.
- **Sanitização de Dados Privados:** Ao salvar projetos como modelos ou seções como blocos (`substituir_placeholders=True`), nomes pessoais, telefones, números de WhatsApp reais e credenciais são substituídos por dados genéricos profissionais.

### 13.2 Catálogo Inicial do Sistema
- **8 Templates Padrão:**
  1. *BioSite Minimal:* Limpo, tipografia forte e espaçamento generoso.
  2. *BioSite Premium:* Dark mode com efeitos glow e cards sofisticados.
  3. *Cartão Digital NFC:* Layout vertical focado em toque rápido e contatos diretos.
  4. *Profissional Moderno:* Focado em médicos, consultores e advogados com CTA e agendamento.
  5. *Profissional Elegante:* Estilo editorial com fontes serifadas e tons neutros.
  6. *Empresa Compacta:* Apresentação institucional ágil com serviços e localização.
  7. *Portfólio Visual:* Focado em criativos e fotógrafos com galerias em grade e carrossel.
  8. *Restaurante & Comércio:* Destaques de cardápio, horários e pedidos via WhatsApp.
- **15 Blocos Reutilizáveis:** Hero Minimal, Hero com Banner, Hero Escuro Glow, Perfil Central, CTA WhatsApp, Links Rápidos, Barra de Redes Sociais, Serviços em Cards, Serviços Compactos, Galeria em Grade, Galeria Horizontal (Carrossel), Agendamento Externo, Localização / Mapa, Contato Direto e Rodapé Minimalista.

### 13.3 Motor de Renderização de Snapshots em Memória
- `RenderizadorBioSite.renderizar_snapshot()`: Renderiza o HTML e CSS Tokens de um template em tempo real **sem gravar nada no banco de dados**, com altíssima performance para pré-visualização.

### 13.4 Interfaces de Usuário
- **Biblioteca de Templates (`/painel/templates/`):** Listagem com busca, filtros por origem (Sistema vs Meus Modelos) e categoria, cards visuais e ações (Visualizar, Usar Modelo, Duplicar, Arquivar, Excluir).
- **Preview 390px Mobile-First (`/painel/templates/<uuid>/preview/`):** Visualização realista com moldura de smartphone, alternador de largura de tela e botão "Usar este modelo".
- **Fluxo "Novo Site" Modernizado (`/painel/sites/novo/`):** Seletor de ponto de partida com card "[ Em branco ]" e cards dos modelos. Ao submeter com modelo selecionado, instancia o projeto e redireciona direto para o editor visual.
- **Integração no Estúdio (`/painel/sites/<uuid>/editor/`):**
  - Aba **BLOCOS** na sidebar esquerda para inserção rápida de seções prontas.
  - Botão **Salvar como Modelo** na topbar do editor.
  - Botão **Salvar como Bloco** (`💾`) no cabeçalho de cada seção do canvas.

### 13.5 Comandos de Gerenciamento
- Carga inicial e sincronização idempotente:
  ```bash
  python manage.py carregar_templates_sistema
  ```
- Auditoria estrutural de todos os modelos e blocos:
  ```bash
  python manage.py validar_templates
  ```

---

## 14. Rascunho, Preview Final, Versionamento, Publicação e Hospedagem (Prompt 8)

### 14.1 Princípio Fundamental: Salvar ≠ Publicar
Inspirado na arquitetura do **Lovable**, a plataforma separa rigorosamente a área de trabalho do produto no ar:
- **Área de Rascunho (Editor):** Autosave contínuo gravando alterações no banco relacional (`PaginaSite`, `SecaoSite`, `ContainerSite`, `ElementoSite`). Alterações no rascunho **nunca** afetam o site público até que uma nova versão seja explicitamente publicada.
- **Área Pública Oficial (`/b/<slug>/`):** Renders exclusivamente a partir de snapshots JSON imutáveis, canônicos e versionados (`PublicacaoSite`).
- **Idempotência:** Tentativas de republicar conteúdo inalterado são detectadas e rejeitadas via hash determinístico SHA-256, evitando versões duplicadas inúteis.

### 14.2 Modelos e Versionamento Imutável
- **`PublicacaoSite`:**
  - `projeto`: FK para `ProjetoSite`.
  - `numero_versao`: Sequencial estrito (`v1`, `v2`, `v3`, ...).
  - `snapshot`: JSONField canônico contendo toda a árvore estrutural congelada, design tokens e metadados.
  - `schema_version`: Versão do esquema JSON (versão 1).
  - `hash_conteudo`: Fingerprint SHA-256 determinístico de 64 caracteres.
  - `publicado_em`: Timestamp exato da publicação.
  - `publicado_por`: Usuário operador autenticado.
  - `ativa`: Booleano identificando a versão atualmente servida ao público.
  - `midias_referenciadas`: ManyToMany para `MidiaSite` que impede exclusão acidental de mídias históricas.
  - Restrição de unicidade: `UniqueConstraint(fields=['projeto', 'numero_versao'])`.
- **Campos em `ProjetoSite`:**
  - `publicacao_ativa`: FK apontando para a publicação no ar.
  - `titulo_seo`, `descricao_seo`, `imagem_compartilhamento`, `indexavel`.
- **Retenção Protetiva de Mídia (`MidiaSite.delete`):**
  - Mídias vinculadas a publicações históricas não podem ser deletadas sem despublicação ou confirmação explícita, prevenindo links e imagens quebradas no site público.

### 14.3 Rollback Cronológico Seguro
Seguindo as melhores práticas de auditabilidade e integridade:
- Restaurar uma versão antiga (ex: restaurar `v1` enquanto se está em `v3`) **não** reativa o registro antigo nem reescreve a história.
- O sistema gera uma **nova versão** (`v4`) com o snapshot e hash de `v1`, preservando o histórico cronológico de auditoria.

### 14.4 Rota Pública Canônica (`/b/<slug>/`)
- **Arquitetura Smartphone-First:** Container responsivo com largura base de 390px (320px–430px mobile, centralizado com background elegante em desktop).
- **SEO & Metatags Completas:**
  - `<title>` customizado ou herdado do projeto.
  - `<meta name="description">` para indexadores.
  - `<meta name="robots" content="index, follow">` (ou `noindex, nofollow` se `indexavel=False`).
  - `<link rel="canonical" href="...">`.
  - Open Graph (`og:title`, `og:description`, `og:image`, `og:url`, `og:type`).
  - Twitter Card tags.
- **Cache & Performance:**
  - Cache em memória/Redis com chave determinística `biosite:publico:<slug>`.
  - Conditional GET com cabeçalho `ETag` (hash do snapshot) retornando `304 Not Modified` sem recalcular templates ou transferir payloads.
  - Retorno HTTP 404 estrito para sites em rascunho, slugs inexistentes ou sites despublicados.

### 14.5 Recursos de Interface
- **Editor Visual (`/painel/sites/<uuid>/editor/`):**
  - Indicador dinâmico de status na topbar (`v1 no ar`, `v1 • Não publicado`, `Rascunho`).
  - Botão `🚀 Publicar` abrindo checklist modal com pré-validação (árvore de páginas, blocos, metadados SEO, URLs inseguras).
  - Modal de sucesso com link público oficial, botão de cópia para área de transferência e botão para abrir em nova aba.
  - Botão `🕘 Versões` exibindo histórico completo com preview isolado de snapshots, rollback no ar, restauração do rascunho no editor e opção de despublicar.
- **Workspace e Detalhes do Projeto:**
  - Badges de publicação nos cards de sites.
  - Seção dedicada "🚀 Publicação & Site no Ar" com link público, dados da versão ativa e histórico de versões.

### 14.6 Comando de Auditoria de Publicações
Para verificar a integridade de todas as publicações no banco de dados:
```bash
python manage.py verificar_publicacoes
```

---

## 15. Subdomínios, Domínios Personalizados e Resolução Segura de Host (Prompt 9)

A plataforma implementa hospedagem centralizada multi-site em uma única instância Django, suportando subdomínios da plataforma e domínios próprios personalizados com isolamento rigoroso de segurança e proteção contra *Host Header Poisoning*.

### 15.1 Modelagem de Endereços (`EnderecoSite` e `HistoricoEnderecoSite`)
- **`EnderecoSite`**: Registra cada host normalizado vinculado a um projeto:
  - Tipo: `SUBDOMINIO_PLATAFORMA` ou `DOMINIO_PERSONALIZADO`.
  - Status: `PENDENTE`, `VERIFICADO`, `ATIVO`, `ERRO`, `REMOVIDO`.
  - Flag `principal`: exatamente um endereço principal ativo por projeto (assegurado por constraint de banco `UniqueConstraint(condition=Q(principal=True))`).
  - `token_verificacao`: token criptograficamente seguro (`secrets.token_urlsafe(32)`).
- **`HistoricoEnderecoSite`**: Registra quarentena de domínios e subdomínios desvinculados por 30 dias, prevenindo ataques de *domain takeover* e colisões imediatas.

### 15.2 Coleção Segura de Hosts (`DynamicAllowedHosts`)
- Django rejeita por padrão qualquer host fora de `ALLOWED_HOSTS` com HTTP 400.
- `DynamicAllowedHosts(list)` provê validação segura em tempo real combinando:
  1. Hosts estáticos da plataforma (`localhost`, `127.0.0.1`, base domain e wildcard `.basedomain`).
  2. Domínios personalizados **ativos ou verificados** consultados no banco e mantidos em cache.
- **Benefício**: Zero reinicialização do servidor ao cadastrar novos domínios e **sem** abrir a brecha insegura de `ALLOWED_HOSTS = ["*"]`.

### 15.3 Resolução Dinâmica e Barreira de Segurança (`HostRoutingMiddleware`)
- **Classificação**: Classifica cada requisição em `HOST_PLATAFORMA`, `HOST_SITE` ou `HOST_DESCONHECIDO`.
- **Barreira de Isolamento Absoluto**: Bloqueia imediatamente requisições a rotas administrativas (`/painel/`, `/admin/`, `/health/`) originadas de domínios de clientes, retornando `HTTP 404`.
- **Entrega Multi-Site na Raiz (`/`)**: O BioSite é servido diretamente na raiz quando acessado pelo host do cliente, sem necessidade de caminhos extras.
- **Redirecionamento de Aliases (301)**: Quando um site possui múltiplos domínios (ex: subdomínio antigo da plataforma e novo domínio customizado), acessos ao alias secundário são redirecionados automaticamente via `301 Permanent Redirect` para o endereço principal.
- **Compatibilidade Retroativa**: A rota legada `/b/<slug>/` permanece plenamente funcional na plataforma.

### 15.4 Verificação Criptográfica via DNS (`servicos_dns.py`)
- Validação assíncrona/on-demand via registro DNS TXT (`_site-verification.<host>` com valor `biosite-verification=<token>`).
- Utilização de `dnspython` com timeout estrito de 3 segundos para proteger o ciclo de requisição.
- Tratamento resiliente de `NXDOMAIN`, `NoAnswer` e `Timeout`.

### 15.5 Auditoria de Domínios
Para auditar a integridade de todos os domínios, duplicidades e múltiplos principais:
```bash
python manage.py verificar_dominios
```

---

## 16. NFC, QR Code e Links Inteligentes (Prompt 10)

Sistema de redirecionamento dinâmico e gestão de tags físicas (NFC e QR Code) com desvinculação absoluta entre o hardware físico/material impresso e o destino web.

### 16.1 O Princípio Central: Imutabilidade da Mídia Física
- Tags físicas (cartões NFC, chaveiros, adesivos, placas de balcão) e QR Codes impressos são gravados com URLs canônicas da plataforma de redirecionamento:
  - NFC: `https://go.seudominio.com/n/<token>/`
  - QR Code: `https://go.seudominio.com/q/<token>/`
- O redirector central resolve em tempo de execução o projeto ativo vinculado e seu endereço canônico atual (`obter_url_publica_projeto`).
- **Benefício**: Se o BioSite alterar seu subdomínio, cadastrar um novo domínio próprio, ou a tag física for reatribuída a outro cliente/projeto, **o chip NFC físico e o material impresso NUNCA precisam ser regravados ou reimpressos**.

### 16.2 Segurança e Isolamento do Redirector
- **HTTP 302 Found**: Redirecionamento temporário para garantir que navegadores não façam cache do destino, permitindo trocas instantâneas de projeto no painel.
- **Isolamento de Cabeçalho Host**: URLs de destino são obtidas puramente do banco de dados e das configurações seguras da plataforma, sem uso de `request.get_host()`, prevenindo ataques de *Host Header Poisoning*.
- **Anti Open-Redirect**: Parâmetros como `?url=` ou `?next=` são estritamente proibidos; o redirector só redireciona para projetos internos válidos.
- **Cookieless & Privacy-First**: As rotas de redirecionamento operam livres de cookies de sessão, rastreamento ou autenticação, com cabeçalho `X-Robots-Tag: noindex, nofollow`.
- **Barreira de Serviço**: O host `go.seudominio.com` bloqueia requisições a rotas administrativas (`/painel/`, `/admin/`).

### 16.3 Gerador de QR Code
- Geração nativa com a biblioteca `qrcode` e `Pillow` utilizando nível de correção de erro **M (15%)** e quiet zone de 4 módulos.
- Permite download e renderização em tamanhos padronizados (256px, 512px, 1024px, 2048px).

### 16.4 Auditoria de Links Inteligentes
Para auditar a unicidade de tokens, links órfãos e integridade do histórico:
```bash
python manage.py verificar_links_inteligentes
```

---

## 17. Qualidade de Código e Lint

Para verificar conformidade com a PEP 8:
```bash
ruff check .
```

Para formatar automaticamente o código:
```bash
ruff format .
```

Para executar a suíte completa de testes automatizados (252 testes):
```bash
python manage.py test --settings=configuracao.settings.teste
```

---

## 18. Próximas Etapas (Prompts 11 a 12)

1. **Prompt 1:** Fundação, Arquitetura e Configuração do Projeto *(Concluído)*
2. **Prompt 2:** Autenticação Privada e Workspace "Meus Sites" *(Concluído)*
3. **Prompt 3:** Clientes, Projetos de Site e Workspace "Meus Sites" Funcional *(Concluído)*
4. **Prompt 4:** Motor Estrutural de Páginas, Seções, Containers e Elementos *(Concluído)*
5. **Prompt 5:** Editor Visual Mobile-First e Preview *(Concluído)*
6. **Prompt 6:** Design System, Propriedades Visuais Avançadas e Componentes Premium *(Concluído)*
7. **Prompt 7:** Biblioteca de Modelos (Templates), Blocos Prontos e Pré-visualização de Temas *(Concluído)*
8. **Prompt 8:** Rascunho, Preview Final, Versionamento, Publicação e Hospedagem *(Concluído — 199 testes)*
9. **Prompt 9:** Subdomínios, Domínios Personalizados e Resolução Segura de Host *(Concluído — 227 testes)*
10. **Prompt 10:** NFC, QR Code e Links Inteligentes *(Concluído — 252 testes)*
11. **Prompt 11:** Hardening, Performance e Telemetria
12. **Prompt 12:** Auditoria e Entrega Final






