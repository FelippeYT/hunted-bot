# 🌊 BIKINI BOTTOM - HUNTED SYSTEM

O **Bikini Bottom Radar** é um ecossistema de monitoramento em tempo real para Tibia. Ele combina um **Bot de Discord** (gerente) com um **Dashboard Web** (visualizador) para rastrear inimigos (Hunted) e aliados (Friends), identificando mortes, níveis e status de conexão.

---

## 🛠️ Arquitetura do Projeto

O sistema funciona através de sincronização de arquivos JSON:
1.  **O Bot (Python):** Gerencia as listas via comandos no Discord e faz o scraping dos dados (Rubinot/Tibia).
2.  **Os Dados (JSON):** Servem como a "ponte" de comunicação entre o script e a interface.
3.  **O Dashboard (HTML/JS):** Lê os arquivos e exibe os dados com filtros avançados e status em tempo real.

---

## 📂 Estrutura de Arquivos

* **`bot_hunted.py`**: O núcleo do sistema. Gerencia o Discord, faz o scraping de dados de mundos e mortes, e gera os alertas de voz (gTTS).
* **`index.html`**: Interface web moderna (Bootstrap) para visualização rápida da situação do servidor.
* **`monitor_data.json`**: Registro histórico de todos os eventos (login, logout, mortes, leveis).
* **`hunted_data.json`**: Base de dados dos jogadores inimigos.
* **`friends_data.json`**: Base de dados dos jogadores aliados.

---

## 🤖 Comandos do Bot (Discord)

### Gerenciamento de Listas
* `!add [Nome]` - Adiciona um jogador à lista de **Hunted**.
* `!remove [Nome]` - Remove um jogador da lista de **Hunted**.
* `!lista` (ou `!list`) - Exibe todos os alvos sendo monitorados.
* `!friend [Nome]` - Adiciona um jogador à lista de **Amigos**.
* `!unfriend [Nome]` - Remove um jogador da lista de **Amigos**.
* `!friends` - Exibe todos os aliados sendo monitorados.

### Utilidades de Voz e Coordenação
* `!masspush` - Puxa todos os membros de outros canais de voz para o seu canal atual (Requer ID autorizado).
* `!masspoke [Mensagem]` - Entra em todos os canais de voz ativos e narra a mensagem via gTTS (Requer ID autorizado).

---

## 📊 Dashboard Web (index.html)

O Dashboard foi projetado para ser intuitivo durante o combate:
* **Status Dinâmico:** Players online sobem automaticamente para o topo com indicador verde neon.
* **Filtros Inteligentes:**
    * **⚔️ PVP:** Isola apenas mortes causadas por outros jogadores (identificadas pelo bot).
    * **👾 PVE:** Mostra mortes para criaturas (Monstros).
    * **💀/💎 Filtros de Grupo:** Alterna a visão entre inimigos e aliados.
* **Histórico Individual:** Clique no card de qualquer player para ver o log detalhado de todas as suas atividades registradas.

---

## 🚀 Como Configurar e Rodar

### 1. Pré-requisitos
* **Python 3.10+**
* **Playwright** (para scraping):
    ```bash
    pip install playwright
    playwright install chromium
    ```
* **Discord.py** e **gTTS**:
    ```bash
    pip install discord.py gtts
    ```

### 2. Configuração Inicial
No arquivo `bot_hunted.py`, configure:
* `TOKEN`: O token do seu bot do Discord.
* `CHANNEL_ID` e `CHANNEL_FRIENDS`: IDs dos canais onde o bot enviará os alertas.
* `AUTHORIZED_IDS`: IDs dos usuários que podem usar comandos administrativos (MassPush/Poke).

### 3. Execução
1.  **Inicie o Bot:**
    ```bash
    python bot_hunted.py
    ```
2.  **Abra o Dashboard:**
    * O navegador bloqueia a leitura de arquivos locais por segurança (CORS). **É obrigatório** usar um servidor local.
    * No VS Code: Use a extensão **Live Server** no `index.html`.
    * Via Terminal: `python -m http.server 8000`.

---

## 🔊 Alertas Sonoros (gTTS)
O sistema utiliza **Google Text-to-Speech** para notificações críticas. Quando configurado, o bot pode narrar entradas de inimigos ou mensagens de sistema diretamente nos canais de voz do Discord.

---

**Desenvolvido para estudo e gerenciamento de guilda.** 🍍🛡️
