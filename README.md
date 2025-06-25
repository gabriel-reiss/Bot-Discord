# 🤖 Bot de Suporte e Utilidades para Discord

> **⚠️ Status do Projeto**: Este bot está atualmente **em desenvolvimento** e encontra-se na **fase beta**. Funcionalidades podem estar incompletas ou sujeitas a mudanças.

Um bot completo para Discord focado em um sistema de tickets eficiente e ferramentas de moderação, desenvolvido com `discord.py`.

## ✨ Funcionalidades

### 🎟️ Sistema de Tickets Avançado
- **Criação via Botões**: Interface intuitiva com botões para cada categoria de suporte.
- **Fila de Espera**: Ao abrir um ticket, o usuário entra em uma fila de espera. Apenas quando um administrador clicar no botão "Pegar próximo ticket" o canal do ticket é criado e atribuído a um atendente.
- **Painel de Fila**: O painel da fila pode ser postado em qualquer canal para a equipe acompanhar e pegar tickets facilmente.
- **Categorias Personalizadas**:
  - 📋 Suporte Geral
  - ⭕ Denúncia
  - 💬 Recrutamento (com campos específicos de Nick, Força e Economia)
  - 🔧 Suporte Técnico
- **Canais Privados**: Cada ticket gera um canal privado, visível apenas para o autor e a equipe.
- **Logs Detalhados**: Todas as ações (criação, fechamento, etc.) são registradas em um canal privado para a staff.

### 📢 Painéis de Informação
- **Crie Anúncios e Regras**: Use o comando `/criar-painel` para montar painéis informativos, como regras do servidor ou anúncios importantes.
- **Publicação Simples**: Poste os painéis criados em qualquer canal com o comando `/postar-painel`.
- **Botão Interativo**: Cada painel pode ter um botão para ações futuras ou links.

### 🛠️ Ferramentas de Moderação
- **/limpar**: Comando para apagar um número específico de mensagens em um canal (requer permissão).

## 🚀 Instalação e Configuração

1.  **Pré-requisitos**:
    - Python 3.8 ou superior
    - Conta de desenvolvedor no Discord com um aplicativo de bot criado.

2.  **Instalação**:
    ```bash
    # Clone este repositório
    git clone <url_do_repositorio>
    cd <nome_do_repositorio>

    # Instale as dependências
    pip install -r requirements.txt
    ```

3.  **Configuração**:
    - Renomeie o arquivo `.env.example` para `.env`.
    - Abra o arquivo `.env` e insira o token do seu bot:
      ```
      DISCORD_BOT_TOKEN="SEU_TOKEN_AQUI"
      ```

4.  **Iniciando o Bot**:
    ```bash
    python bot.py
    ```

## 📋 Comandos Essenciais no Discord

### Comandos de Administrador
- `/config-bot`: Define o canal de logs e o cargo da equipe de suporte.
  - *Exemplo: `/config-bot log_channel:#logs staff_role:@Equipe`*
- `/setup-suporte`: Cria o painel principal com os botões para abrir tickets.
- `/criar-painel`: Abre um formulário para criar um novo painel de informações (regras, anúncios, etc.).
- `/postar-painel`: Publica um painel já criado no canal atual.
- `/fila-tickets`: Exibe a fila de espera de tickets e permite que administradores peguem o próximo ticket através de um botão interativo.
- `/postar-fila-tickets`: Posta o painel da fila de tickets (com botão para admins) em um canal específico.
- `/refresh-bot`: Sincroniza os comandos do bot com o Discord.

> **Comandos de administrador só aparecem para quem tem permissão de administrador no servidor.**

### Comandos da Equipe (Staff)
- `/limpar`: Apaga mensagens do canal.
  - *Exemplo: `/limpar quantidade:50`*
- `/listar-tickets`: Mostra uma lista de tickets, com filtros por status ou categoria.
- `/logs-ticket`: Exibe o histórico de um ticket específico.
- `/fechar-ticket`: Fecha o ticket no canal atual.
- `/transferir-ticket`: Muda o proprietário de um ticket para outro usuário.

### Comandos para Usuários
- `/meus-tickets`: Lista todos os tickets que você já criou.

---

Para dúvidas ou sugestões, abra uma issue ou entre em contato com a equipe de desenvolvimento.

