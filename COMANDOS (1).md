# 📋 Guia de Comandos do Bot

Este guia detalha todos os comandos disponíveis no bot, separados por nível de permissão.

---

## 👑 Comandos de Administrador

### `/config-bot`
- **Descrição:** Configura as definições essenciais do bot, como o canal de logs e o cargo da equipe.
- **Parâmetros:**
  - `log_channel` (Obrigatório): O canal de texto para onde os logs de tickets serão enviados.
  - `staff_role` (Obrigatório): O cargo que terá permissões de staff nos tickets e comandos.
- **Exemplo:** `/config-bot log_channel:#logs-da-staff staff_role:@Equipe`

### `/setup-suporte`
- **Descrição:** Posta o painel principal de suporte no canal onde o comando é executado. Este painel contém os botões para os usuários abrirem os tickets.
- **Uso:** `/setup-suporte`

### `/criar-painel`
- **Descrição:** Abre um formulário (modal) para criar ou editar um painel de informações customizado (ex: regras, anúncios).
- **Uso:** `/criar-painel`
- **Campos do Formulário:**
  - `Nome único`: Um identificador para o painel (ex: `regras`, `anuncios-vip`).
  - `Título do Embed`: O título principal do painel.
  - `Texto do Botão`: O texto que aparecerá no botão do painel.
  - `Conteúdo Principal`: O corpo do texto do seu anúncio ou regras.

### `/postar-painel`
- **Descrição:** Publica um painel de informações previamente criado em um canal.
- **Parâmetros:**
  - `nome` (Obrigatório): O nome único que você definiu ao usar `/criar-painel`.
- **Exemplo:** `/postar-painel nome:regras`

### `/stats-tickets`
- **Descrição:** Mostra estatísticas detalhadas sobre os tickets do servidor.
- **Uso:** `/stats-tickets`

### `/fila-tickets`
- **Descrição:** Exibe a fila de espera de tickets e permite que administradores peguem o próximo ticket através de um botão interativo.
- **Uso:** `/fila-tickets`

### `/postar-fila-tickets`
- **Descrição:** Posta o painel da fila de tickets (com botão para admins) em um canal específico.
- **Parâmetros:**
  - `canal` (Obrigatório): O canal de texto onde o painel será postado.
- **Exemplo:** `/postar-fila-tickets canal:#atendimento-staff`

### `/refresh-bot`
- **Descrição:** Força a sincronização dos comandos slash com o Discord. Útil se algum comando novo não estiver aparecendo.
- **Uso:** `/refresh-bot`

> **Observação:** Comandos de administrador só aparecem para quem tem permissão de administrador no servidor.

---

## 🛡️ Comandos da Equipe (Staff)

### `/limpar`
- **Descrição:** Apaga um número de mensagens no canal atual.
- **Parâmetros:**
  - `quantidade` (Opcional): O número de mensagens a serem apagadas (1 a 100, padrão: 10).
- **Exemplo:** `/limpar quantidade:25`
- **Permissão Necessária:** Gerenciar Mensagens.

### `/listar-tickets`
- **Descrição:** Lista os tickets do servidor, com a opção de filtrar por status ou categoria.
- **Parâmetros:**
  - `status` (Opcional): `aberto` ou `fechado`.
  - `categoria` (Opcional): `ticket_geral`, `denuncia`, `recrutamento`, `suporte_tecnico`.
- **Exemplo:** `/listar-tickets status:aberto categoria:recrutamento`

### `/logs-ticket`
- **Descrição:** Exibe o histórico completo de ações de um ticket específico.
- **Parâmetros:**
  - `ticket_id` (Obrigatório): O ID do ticket.
- **Exemplo:** `/logs-ticket ticket_id:42`

### `/ver-ticket`
- **Descrição:** Mostra as informações detalhadas de um ticket pelo seu ID.
- **Parâmetros:**
  - `ticket_id` (Obrigatório): O ID do ticket.
- **Exemplo:** `/ver-ticket ticket_id:42`

### `/fechar-ticket`
- **Descrição:** Fecha o ticket no canal em que o comando é utilizado. O canal será deletado em seguida.
- **Uso:** `/fechar-ticket`

### `/transferir-ticket`
- **Descrição:** Transfere a propriedade de um ticket para outro usuário.
- **Parâmetros:**
  - `novo_usuario` (Obrigatório): O membro do Discord que será o novo dono do ticket.
- **Exemplo:** `/transferir-ticket novo_usuario:@Usuario`

---

## 👤 Comandos para Usuários

### `/meus-tickets`
- **Descrição:** Mostra uma lista de todos os tickets que você já criou, incluindo o status e a data de criação.
- **Uso:** `/meus-tickets`

> **Observação:** Comandos de usuário são visíveis para todos os membros do servidor.
