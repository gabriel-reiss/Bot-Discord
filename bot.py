import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
import asyncio

# Carregar variáveis do arquivo .env
load_dotenv()

def get_bot_token():
    token_vars = ['DISCORD_BOT_TOKEN', 'DISCORD_TOKEN', 'BOT_TOKEN', 'TOKEN']
    for var_name in token_vars:
        token = os.getenv(var_name)
        if token:
            token = token.strip().strip('"').strip("'")
            if token and len(token) > 50:
                print(f"✅ Token encontrado na variável: {var_name}")
                return token
    return None

TOKEN = get_bot_token()

if not TOKEN:
    print("❌ ERRO: Token do bot não encontrado!")
    print("📝 Configure o token no arquivo .env")
    exit(1)

print(f"🔑 Token carregado: {TOKEN[:10]}...{TOKEN[-5:]}")

# Configurar intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True

# Criar bot com prefixo '!' e intents configuradas
bot = commands.Bot(command_prefix='!', intents=intents)

# Configurações globais
TICKET_CATEGORY_NAME = "🎫 TICKETS"
LOG_CHANNEL_NAME = "📋-logs-tickets"

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar banco de dados
def init_database():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    # Criação das tabelas do banco
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'aberto',
            channel_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_by TEXT,
            closed_at TIMESTAMP,
            assigned_to TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            guild_id TEXT PRIMARY KEY,
            ticket_category_id TEXT,
            log_channel_id TEXT,
            staff_role_id TEXT,
            suggestion_channel_id TEXT,
            approved_suggestion_channel_id TEXT,
            fila_channel_id TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco INTEGER NOT NULL,
            estoque INTEGER DEFAULT 0,
            pix_code TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_inventory (
            user_id TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_id),
            FOREIGN KEY (item_id) REFERENCES shop_items(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id TEXT PRIMARY KEY,
            saldo INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            UNIQUE(guild_id, name)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stream_notifications (
            streamer_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            custom_message TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS info_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            title TEXT,
            content TEXT,
            UNIQUE(guild_id, name)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("💾 Banco de dados inicializado!")

# Criar log no banco de dados
async def create_log(ticket_id: int, action: str, user: discord.User, details: str = None):
    try:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ticket_logs (ticket_id, action, user_id, username, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticket_id, action, str(user.id), user.display_name, details))
        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao criar log: {e}")
    finally:
        conn.close()

# Enviar embed de log para o canal configurado
async def send_log_to_channel(guild: discord.Guild, embed: discord.Embed):
    try:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT log_channel_id FROM bot_config WHERE guild_id = ?', (str(guild.id),))
        result = cursor.fetchone()
        if result and result[0]:
            log_channel = guild.get_channel(int(result[0]))
            if log_channel and isinstance(log_channel, discord.TextChannel):
                await log_channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Erro ao enviar log para canal: {e}")
    finally:
        conn.close()

# Obter ou criar categoria de tickets
async def get_or_create_ticket_category(guild: discord.Guild):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ticket_category_id, log_channel_id, staff_role_id FROM bot_config WHERE guild_id = ?', (str(guild.id),))
        result = cursor.fetchone()
        log_channel_id = result[1] if result else None
        staff_role_id = result[2] if result else None
        # Se já existe, retorna a categoria
        if result and result[0]:
            category = guild.get_channel(int(result[0]))
            if category and isinstance(category, discord.CategoryChannel):
                return category
        
        # Criar a categoria se não existir
        category = await guild.create_category(
            TICKET_CATEGORY_NAME,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }
        )
        cursor.execute('''
            INSERT OR REPLACE INTO bot_config (guild_id, ticket_category_id, log_channel_id, staff_role_id)
            VALUES (?, ?, ?, ?)
        ''', (str(guild.id), str(category.id), log_channel_id, staff_role_id))
        conn.commit()
        return category
    except Exception as e:
        print(f"❌ Erro ao obter/criar categoria: {e}")
    finally:
        conn.close()

# View com botões para tipos de suporte
class SupportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _create_ticket_modal(self, interaction: discord.Interaction, category_name: str, category_value: str):
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM tickets WHERE user_id = ? AND status = "aberto"', (str(interaction.user.id),))
        existing_ticket = cursor.fetchone()
        conn.close()
        
        if existing_ticket:
            await interaction.response.send_message(
                f"❌ Você já possui um ticket aberto (#{existing_ticket[0]}). Feche-o antes de criar um novo.",
                ephemeral=True
            )
            return
        
        modal = TicketModal(category_name, category_value)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Abrir ticket", style=discord.ButtonStyle.secondary, emoji="📋")
    async def ticket_geral(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket_modal(interaction, "📋 Suporte Geral", "ticket_geral")

    @discord.ui.button(label="Denunciar", style=discord.ButtonStyle.danger, emoji="⭕")
    async def denuncia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket_modal(interaction, "⭕ Denúncia", "denuncia")

    @discord.ui.button(label="Recrutamento", style=discord.ButtonStyle.primary, emoji="💬")
    async def recrutamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket_modal(interaction, "💬 Recrutamento", "recrutamento")
        
    @discord.ui.button(label="Suporte Técnico", style=discord.ButtonStyle.secondary, emoji="🔧")
    async def suporte_tecnico(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket_modal(interaction, "🔧 Suporte Técnico", "suporte_tecnico")

# Modal para criação de ticket com campos dinâmicos
class TicketModal(discord.ui.Modal):
    def __init__(self, category_name: str, category_value: str):
        super().__init__(title=f"Criar {category_name}")
        
        self.category_name = category_name
        self.category_value = category_value
        
        if category_value == "denuncia":
            self.title_field = discord.ui.TextInput(
                label="Nome do jogador denunciado",
                placeholder="Digite o nome do jogador...",
                required=True,
                max_length=100
            )
            self.description_field = discord.ui.TextInput(
                label="Motivo da denúncia",
                placeholder="Descreva o comportamento inadequado...",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000
            )
            self.add_item(self.title_field)
            self.add_item(self.description_field)

        elif category_value == "recrutamento":
            self.nick_field = discord.ui.TextInput(
                label="Nick do jogador",
                placeholder="Digite seu nick", #nick 
                required=True,
                max_length=100
            )
            self.forca_field = discord.ui.TextInput(
                label="Força",
                placeholder="Informe sua força total (ex: 1.5b)", #forca
                required=True,
                max_length=100
            )
            self.economia_field = discord.ui.TextInput(
                label="Economia",
                placeholder="Informe sua economia total (ex: 200m)", #money
                required=True,
                max_length=100
            )
            self.add_item(self.nick_field)
            self.add_item(self.forca_field)
            self.add_item(self.economia_field)
        else:
            self.title_field = discord.ui.TextInput(
                label="Título do ticket",
                placeholder="Descreva brevemente seu problema...",
                required=True,
                max_length=100
            )
            self.description_field = discord.ui.TextInput(
                label="Descrição",
                placeholder="Forneça mais detalhes sobre sua solicitação...",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000
            )
            self.add_item(self.title_field)
            self.add_item(self.description_field)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Adicionar à fila de espera em vez de criar o canal
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM ticket_queue WHERE user_id = ? AND category = ?', (str(interaction.user.id), self.category_value))
            existing_in_queue = cursor.fetchone()
            cursor.execute('SELECT id FROM tickets WHERE user_id = ? AND status = "aberto"', (str(interaction.user.id),))
            existing_ticket = cursor.fetchone()
            if existing_in_queue:
                await interaction.response.send_message(
                    f"❌ Você já está na fila de espera para um ticket desta categoria.",
                    ephemeral=True
                )
                conn.close()
                return
            if existing_ticket:
                await interaction.response.send_message(
                    f"❌ Você já possui um ticket aberto (#{existing_ticket[0]}). Feche-o antes de criar um novo.",
                    ephemeral=True
                )
                conn.close()
                return
            if self.category_value == "recrutamento":
                title_value = f"Recrutamento: {self.nick_field.value}"
                description_value = f"**Força:** {self.forca_field.value}\n**Economia:** {self.economia_field.value}"
            else:
                title_value = self.title_field.value
                description_value = self.description_field.value
            cursor.execute('''
                INSERT INTO ticket_queue (user_id, username, category, title, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(interaction.user.id),
                interaction.user.display_name,
                self.category_value,
                title_value,
                description_value
            ))
            conn.commit()
            conn.close()
            response_embed = discord.Embed(
                title="🕒 Ticket adicionado à fila de espera!",
                description=f"Seu ticket foi adicionado à fila. Aguarde um atendente.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=response_embed, ephemeral=True)

            # Notificar canal de fila configurado em bot_config, se existir
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('SELECT staff_role_id, fila_channel_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
            config_result = cursor.fetchone()
            staff_mention = f"<@&{config_result[0]}>" if config_result and config_result[0] else "@everyone"
            fila_channel = interaction.guild.get_channel(int(config_result[1])) if config_result and config_result[1] else None
            conn.close()
            if fila_channel:
                # Enviar painel com botão para pegar o ticket, sem mensagem de texto
                embed = discord.Embed(
                    title="🕒 Novo ticket na fila de espera!",
                    description=f"Categoria: {self.category_name}\nTítulo: {title_value}",
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Atendente", value=f"Aguardando {staff_mention}", inline=False)
                await fila_channel.send(embed=embed, view=TicketQueueView())
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao adicionar à fila: {e}", ephemeral=True)

# View para controlar canal de ticket com botões
class TicketChannelView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
    # Nenhum botão, apenas estrutura para possíveis futuras interações

# Modal para adicionar usuário ao canal de ticket
class AddUserModal(discord.ui.Modal):
    def __init__(self, ticket_id: int):
        super().__init__(title="Adicionar Usuário ao Ticket")
        self.ticket_id = ticket_id
        
        self.user_input = discord.ui.TextInput(
            label="ID ou @menção do usuário",
            placeholder="Digite o ID ou mencione o usuário...",
            required=True,
            max_length=64
        )
        self.add_item(self.user_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = self.user_input.value.strip()
            user_id = None
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = user_input[2:-1]
                if user_id.startswith('!'):
                    user_id = user_id[1:]
            else:
                user_id = user_input
            
            user = interaction.guild.get_member(int(user_id))
            if not user:
                await interaction.response.send_message("❌ Usuário não encontrado.", ephemeral=True)
                return
            
            await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
            await create_log(self.ticket_id, "USUARIO_ADICIONADO", interaction.user, f"Usuário adicionado: {user}")
            
            embed = discord.Embed(
                title="➕ Usuário Adicionado",
                description=f"{user.mention} foi adicionado ao ticket por {interaction.user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message("❌ ID de usuário inválido.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao adicionar usuário: {e}", ephemeral=True)

# Comandos de prefixo
@bot.command(name='test')
async def test_command(ctx):
    """Comando de teste"""
    await ctx.send("🤖 Bot funcionando perfeitamente!")

@bot.command(name='painel')
async def criar_painel(ctx):
    """Criar painel de suporte"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você precisa ser administrador para usar este comando!")
        return
    try:
        embed = discord.Embed(
            title="🔧 Suporte",
            description="Clique no botão relacionado com o tipo de suporte que deseja",
            color=0x5DADE2
        )
        embed.add_field(name="📋 Abrir ticket", value="Suporte geral e dúvidas", inline=True)
        embed.add_field(name="🚨 Denunciar um jogador", value="Reportar comportamento inadequado", inline=True)
        embed.add_field(name="💬 Recrutamento", value="Recrutamento Guilda", inline=True)
        embed.add_field(name="🔧 Resolução de Problemas", value="Suporte técnico especializado", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        embed.set_footer(text=f"{ctx.guild.name} ©", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        select_view = SupportView()
        
        await ctx.send("✅ Criando painel de suporte...")
        await ctx.send(embed=embed, view=select_view)
    except Exception as e:
        await ctx.send(f"❌ Erro ao criar painel: {e}")

@bot.command(name='config')
async def config_command(ctx, log_channel: discord.TextChannel = None, staff_role: discord.Role = None):
    """Configurar bot"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você precisa ser administrador!")
        return
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT ticket_category_id, log_channel_id, staff_role_id FROM bot_config WHERE guild_id = ?', (str(ctx.guild.id),))
    row = cursor.fetchone()
    ticket_category_id = row[0] if row else None
    log_channel_id = str(log_channel.id) if log_channel else (row[1] if row else None)
    staff_role_id = str(staff_role.id) if staff_role else (row[2] if row else None)
    cursor.execute('''
        INSERT OR REPLACE INTO bot_config (guild_id, ticket_category_id, log_channel_id, staff_role_id)
        VALUES (?, ?, ?, ?)
    ''', (
        str(ctx.guild.id),
        ticket_category_id,
        log_channel_id,
        staff_role_id
    ))
    conn.commit()
    conn.close()
    
    embed = discord.Embed(title="⚙️ Configuração Atualizada", color=discord.Color.green())
    if log_channel:
        embed.add_field(name="📋 Canal de Logs", value=log_channel.mention, inline=True)
    if staff_role:
        embed.add_field(name="👥 Role da Equipe", value=staff_role.mention, inline=True)
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} está online!')
    
    try:
        synced = await bot.tree.sync()
        print(f'📋 Comandos sincronizados: {len(synced)} comandos')
        for cmd in synced:
            print(f"   • /{cmd.name}")
    except Exception as e:
        print(f'❌ Erro ao sincronizar comandos: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT suggestion_channel_id FROM bot_config WHERE guild_id = ?", (str(message.guild.id),))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] and message.channel.id == int(result[0]):
        try:
            await message.delete()
            
            embed = discord.Embed(
                description=message.content,
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.set_author(name=f"Sugestão de {message.author.display_name}", icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"ID da Sugestão: {message.id}")

            sent_message = await message.channel.send(embed=embed)
            await sent_message.add_reaction("👍")
            await sent_message.add_reaction("👎")
        except Exception as e:
            print(f"Erro no sistema de sugestões: {e}")

# Comandos Slash
@bot.tree.command(name="config-bot", description="Configurar canais e roles do bot (apenas administradores)")
@app_commands.describe(
    log_channel="Canal para logs de tickets",
    staff_role="Role da equipe de suporte"
)
@app_commands.checks.has_permissions(administrator=True)
async def config_bot(
    interaction: discord.Interaction,
    log_channel: discord.TextChannel = None,
    staff_role: discord.Role = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você precisa ser administrador para usar este comando.", ephemeral=True)
        return
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT ticket_category_id, log_channel_id, staff_role_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
    row = cursor.fetchone()
    ticket_category_id = row[0] if row else None
    log_channel_id = str(log_channel.id) if log_channel else (row[1] if row else None)
    staff_role_id = str(staff_role.id) if staff_role else (row[2] if row else None)
    cursor.execute('''
        INSERT OR REPLACE INTO bot_config (guild_id, ticket_category_id, log_channel_id, staff_role_id)
        VALUES (?, ?, ?, ?)
    ''', (
        str(interaction.guild.id),
        ticket_category_id,
        log_channel_id,
        staff_role_id
    ))
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="⚙️ Configuração Atualizada",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    if log_channel:
        embed.add_field(name="📋 Canal de Logs", value=log_channel.mention, inline=True)
    if staff_role:
        embed.add_field(name="👥 Role da Equipe", value=staff_role.mention, inline=True)
    embed.set_footer(text="Configurações salvas com sucesso!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup-suporte", description="Criar o painel de suporte (apenas administradores)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_suporte(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você precisa ser administrador para usar este comando.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔧 Suporte",
        description="Clique no botão relacionado com o tipo de suporte que deseja",
        color=0x5DADE2
    )
    embed.add_field(name="📋 Abrir ticket", value="Suporte geral e dúvidas", inline=True)
    embed.add_field(name="⭕ Denunciar um jogador", value="Reportar comportamento inadequado", inline=True)
    embed.add_field(name="💬 Recrutamento", value="Recrutamento Guilda", inline=True)
    embed.add_field(name="🔧 Resolução de Problemas", value="Suporte técnico especializado", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.set_footer(text=f"{interaction.guild.name} ©", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    select_view = SupportView()
    
    await interaction.response.send_message(embed=embed, view=select_view)

@bot.tree.command(name="logs-ticket", description="Ver logs de um ticket específico")
@app_commands.describe(ticket_id="ID do ticket")
@app_commands.checks.has_permissions(administrator=True)
async def logs_ticket(interaction: discord.Interaction, ticket_id: int):
    is_admin = interaction.user.guild_permissions.administrator
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM tickets WHERE id = ?', (ticket_id,))
    ticket_result = cursor.fetchone()
    if not ticket_result:
        await interaction.response.send_message(f"❌ Ticket #{ticket_id} não encontrado.", ephemeral=True)
        conn.close()
        return
    is_owner = str(interaction.user.id) == ticket_result[0]
    
    cursor.execute('SELECT staff_role_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
    staff_result = cursor.fetchone()
    is_staff = False
    if staff_result and staff_result[0]:
        staff_role = interaction.guild.get_role(int(staff_result[0]))
        if staff_role and staff_role in interaction.user.roles:
            is_staff = True
    
    if not (is_owner or is_admin or is_staff):
        await interaction.response.send_message("❌ Você não tem permissão para ver os logs deste ticket.", ephemeral=True)
        conn.close()
        return
    
    cursor.execute('''
        SELECT action, username, details, timestamp 
        FROM ticket_logs 
        WHERE ticket_id = ? 
        ORDER BY timestamp ASC
    ''', (ticket_id,))
    logs = cursor.fetchall()
    conn.close()
    
    if not logs:
        await interaction.response.send_message(f"📋 Nenhum log encontrado para o ticket #{ticket_id}.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📋 Logs do Ticket #{ticket_id}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    log_text = ""
    emoji_map = {"CRIADO": "🎫", "FECHADO": "🔒", "USUARIO_ADICIONADO": "➕", "MENSAGEM": "💬"}
    for action, username, details, timestamp in logs:
        emoji = emoji_map.get(action, "📝")
        details_text = f" - {details}" if details else ""
        log_text += f"{emoji} **{action}** por {username}{details_text}\n`{timestamp}`\n\n"
    
    if len(log_text) > 4096:
        log_text = log_text[:4090] + "..."
    embed.description = log_text
    embed.set_footer(text="Logs ordenados por data de criação")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="listar-tickets", description="Listar todos os tickets (apenas staff)")
@app_commands.describe(status="Filtrar por status", categoria="Filtrar por categoria")
@app_commands.checks.has_permissions(administrator=True)
async def listar_tickets(interaction: discord.Interaction, status: str = None, categoria: str = None):
    is_admin = interaction.user.guild_permissions.administrator
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT staff_role_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
    staff_result = cursor.fetchone()
    is_staff = False
    if staff_result and staff_result[0]:
        staff_role = interaction.guild.get_role(int(staff_result[0]))
        if staff_role and staff_role in interaction.user.roles:
            is_staff = True
    if not (is_admin or is_staff):
        await interaction.response.send_message("❌ Você precisa ser staff para usar este comando.", ephemeral=True)
        conn.close()
        return
    
    query = "SELECT id, username, category, title, status, created_at FROM tickets WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if categoria:
        query += " AND category = ?"
        params.append(categoria)
    query += " ORDER BY created_at DESC LIMIT 20"
    
    cursor.execute(query, params)
    tickets = cursor.fetchall()
    conn.close()
    
    if not tickets:
        await interaction.response.send_message("📋 Nenhum ticket encontrado com os filtros especificados.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📋 Lista de Tickets",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    category_emojis = {
        "ticket_geral": "📋",
        "denuncia": "⭕",
        "recrutamento": "💬",
        "suporte_tecnico": "🔧"
    }
    for ticket in tickets:
        ticket_id, username, category, title, ticket_status, created_at = ticket
        status_emoji = "🟢" if ticket_status == "aberto" else "🔴"
        category_emoji = category_emojis.get(category, "📋")
        embed.add_field(
            name=f"{status_emoji} Ticket #{ticket_id}",
            value=f"{category_emoji} **{title}**\nPor: {username}\nCriado: {created_at[:10]}",
            inline=True
        )
    embed.set_footer(text="Mostrando até 20 tickets mais recentes")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stats-tickets", description="Ver estatísticas dos tickets (apenas administradores)")
@app_commands.checks.has_permissions(administrator=True)
async def stats_tickets(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você precisa ser administrador para usar este comando.", ephemeral=True)
        return
    try:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM tickets')
        total_tickets = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "aberto"')
        tickets_abertos = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "fechado"')
        tickets_fechados = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM tickets')
        usuarios_unicos = cursor.fetchone()[0]
        cursor.execute('SELECT category, COUNT(*) FROM tickets GROUP BY category ORDER BY COUNT(*) DESC')
        stats_categoria = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM tickets WHERE DATE(created_at) = DATE("now")')
        tickets_hoje = cursor.fetchone()[0]
        conn.close()
        
        embed = discord.Embed(
            title="📊 Estatísticas dos Tickets",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📋 Total de Tickets", value=str(total_tickets), inline=True)
        embed.add_field(name="🟢 Tickets Abertos", value=str(tickets_abertos), inline=True)
        embed.add_field(name="🔴 Tickets Fechados", value=str(tickets_fechados), inline=True)
        embed.add_field(name="👥 Usuários Únicos", value=str(usuarios_unicos), inline=True)
        embed.add_field(name="📅 Criados Hoje", value=str(tickets_hoje), inline=True)
        
        if total_tickets > 0:
            taxa_fechamento = (tickets_fechados / total_tickets) * 100
            embed.add_field(name="📈 Taxa de Fechamento", value=f"{taxa_fechamento:.1f}%", inline=True)
        
        if stats_categoria:
            category_names = {
                "ticket_geral": "📋 Suporte Geral",
                "denuncia": "⭕ Denúncias",
                "recrutamento": "💬 Recrutamento",
                "suporte_tecnico": "🔧 Suporte Técnico"
            }
            categoria_text = "\n".join(f"{category_names.get(cat, cat)}: {count}" for cat, count in stats_categoria)
            embed.add_field(name="📂 Por Categoria", value=categoria_text, inline=False)
        
        embed.set_footer(text="Estatísticas atualizadas em tempo real")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao buscar estatísticas: {e}", ephemeral=True)

@bot.tree.command(name="meus-tickets", description="Ver todos os seus tickets")
async def meus_tickets(interaction: discord.Interaction):
    try:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, category, title, status, created_at FROM tickets WHERE user_id = ? ORDER BY created_at DESC', (str(interaction.user.id),))
        tickets = cursor.fetchall()
        conn.close()
        
        if not tickets:
            embed = discord.Embed(
                title="📋 Seus Tickets",
                description="Você ainda não criou nenhum ticket.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use o painel de suporte para criar seu primeiro ticket!")
        else:
            embed = discord.Embed(
                title="📋 Seus Tickets",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            category_emojis = {
                "ticket_geral": "📋",
                "denuncia": "⭕",
                "recrutamento": "💬",
                "suporte_tecnico": "🔧"
            }
            for ticket in tickets[:10]:
                ticket_id, category, title, status, created_at = ticket
                status_emoji = "🟢" if status == "aberto" else "🔴"
                category_emoji = category_emojis.get(category, "📋")
                embed.add_field(
                    name=f"{status_emoji} Ticket #{ticket_id}",
                    value=f"{category_emoji} **{title}**\nStatus: {status}\nCriado: {created_at[:10]}",
                    inline=True
                )
            footer_text = f"Mostrando 10 de {len(tickets)} tickets" if len(tickets) > 10 else "Use /logs-ticket <id> para ver logs detalhados"
            embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao buscar tickets: {e}", ephemeral=True)

@bot.tree.command(name="ver-ticket", description="Mostra as informações de um ticket pelo seu ID.")
@app_commands.describe(ticket_id="O ID do ticket que você deseja visualizar.")
async def ver_ticket(interaction: discord.Interaction, ticket_id: int):
    try:
        is_admin = interaction.user.guild_permissions.administrator
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM tickets WHERE id = ?', (ticket_id,))
        ticket_owner_result = cursor.fetchone()

        if not ticket_owner_result:
            await interaction.response.send_message(f"❌ Ticket #{ticket_id} não foi encontrado.", ephemeral=True)
            conn.close()
            return

        is_owner = str(interaction.user.id) == ticket_owner_result[0]

        cursor.execute('SELECT staff_role_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
        staff_result = cursor.fetchone()
        is_staff = False
        if staff_result and staff_result[0]:
            staff_role = interaction.guild.get_role(int(staff_result[0]))
            if staff_role and staff_role in interaction.user.roles:
                is_staff = True

        if not (is_owner or is_admin or is_staff):
            await interaction.response.send_message("❌ Você não tem permissão para visualizar este ticket.", ephemeral=True)
            conn.close()
            return

        cursor.execute('SELECT user_id, username, category, title, description, status, channel_id, created_at FROM tickets WHERE id = ?', (ticket_id,))
        ticket_data = cursor.fetchone()
        conn.close()

        user_id, username, category, title, description, status, channel_id, created_at = ticket_data
        
        category_map = {
            "ticket_geral": "📋 Suporte Geral",
            "denuncia": "⭕ Denúncia",
            "recrutamento": "💬 Recrutamento",
            "suporte_tecnico": "🔧 Suporte Técnico"
        }
        category_name = category_map.get(category, category.replace('_', ' ').title())

        status_emoji = "🟢" if status == "aberto" else "🔴"
        status_text = "Aberto" if status == "aberto" else "Fechado"
        
        embed = discord.Embed(
            title=f"{status_emoji} Ticket #{ticket_id}: {title}",
            color=discord.Color.blue(),
            timestamp=datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
        )

        ticket_owner = interaction.guild.get_member(int(user_id))
        owner_mention = ticket_owner.mention if ticket_owner else f"{username} (ID: {user_id})"

        embed.add_field(name="👤 Criado por", value=owner_mention, inline=True)
        embed.add_field(name="📂 Categoria", value=category_name, inline=True)
        embed.add_field(name="🔄 Status", value=status_text, inline=True)
        
        cursor.execute('SELECT assigned_to FROM tickets WHERE id = ?', (ticket_id,))
        assigned_result = cursor.fetchone()
        if assigned_result and assigned_result[0]:
            assigned_to_id = assigned_result[0]
            assignee = interaction.guild.get_member(int(assigned_to_id))
            embed.add_field(name="👨‍💻 Atribuído a", value=assignee.mention if assignee else "ID: " + assigned_to_id, inline=True)

        embed.add_field(name="📄 Descrição", value=description, inline=False)

        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
        if channel and status == "aberto":
            embed.add_field(name="🔗 Canal", value=channel.mention, inline=False)

        embed.set_footer(text=f"Criado em")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao buscar o ticket: {e}", ephemeral=True)

@bot.tree.command(name="fechar-ticket", description="Fechar o ticket deste canal (apenas staff, admin ou dono)")
async def fechar_ticket(interaction: discord.Interaction):
    try:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, user_id, title, status FROM tickets WHERE channel_id = ?', (str(interaction.channel.id),))
        ticket = cursor.fetchone()
        if not ticket:
            await interaction.response.send_message("❌ Este canal não é um ticket válido.", ephemeral=True)
            conn.close()
            return
        ticket_id, user_id, title, status = ticket
        
        if status == "fechado":
            await interaction.response.send_message("⚠️ Este ticket já está fechado.", ephemeral=True)
            conn.close()
            return
            
        is_owner = str(interaction.user.id) == user_id
        is_admin = interaction.user.guild_permissions.administrator
        
        cursor.execute('SELECT staff_role_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
        staff_result = cursor.fetchone()
        
        is_staff = False
        if staff_result and staff_result[0]:
            staff_role = interaction.guild.get_role(int(staff_result[0]))
            if staff_role and staff_role in interaction.user.roles:
                is_staff = True
        
        if not (is_owner or is_admin or is_staff):
            await interaction.response.send_message("❌ Você não tem permissão para fechar este ticket.", ephemeral=True)
            conn.close()
            return

        # Se admin ou staff fecha, mostra o modal
        if is_admin or is_staff:
            modal = CloseTicketModal(ticket_id=ticket_id, ticket_owner_id=int(user_id), ticket_title=title)
            await interaction.response.send_modal(modal)
            conn.close()
            return

        # Se o dono fecha, o ticket fecha diretamente
        if is_owner:
            await interaction.response.defer() 

            cursor.execute('''
                UPDATE tickets 
                SET status = "fechado", updated_at = CURRENT_TIMESTAMP, closed_by = ?, closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (str(interaction.user.id), ticket_id))
            conn.commit()
            
            await create_log(ticket_id, "FECHADO", interaction.user)
            
            close_embed = discord.Embed(
                title="🔒 Ticket Fechado",
                description=f"O ticket #{ticket_id} foi fechado por {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            await interaction.followup.send(embed=close_embed)
            
            log_embed = discord.Embed(
                title="🔒 Ticket Fechado",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="📋 ID", value=f"#{ticket_id}", inline=True)
            log_embed.add_field(name="👤 Fechado por", value=f"{interaction.user} ({interaction.user.id})", inline=True)
            log_embed.add_field(name="📝 Título", value=title, inline=False)
            await send_log_to_channel(interaction.guild, log_embed)
            
            await asyncio.sleep(10)
            await interaction.channel.delete(reason=f"Ticket #{ticket_id} fechado")
            conn.close()

    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Erro ao fechar ticket: {e}", ephemeral=True)
        else:
            print(f"Error in fechar_ticket after response was sent: {e}")

class CloseTicketModal(discord.ui.Modal, title="Fechar Ticket com Motivo"):
    def __init__(self, ticket_id: int, ticket_owner_id: int, ticket_title: str):
        super().__init__()
        self.ticket_id = ticket_id
        self.ticket_owner_id = ticket_owner_id
        self.ticket_title = ticket_title
        
        self.reason = discord.ui.TextInput(
            label="Motivo do Fechamento",
            style=discord.TextStyle.paragraph,
            placeholder="Este motivo será enviado ao usuário que abriu o ticket.",
            required=True,
            max_length=500
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Enviar DM para o usuário
        ticket_owner = interaction.guild.get_member(self.ticket_owner_id)
        if ticket_owner:
            try:
                dm_embed = discord.Embed(
                    title=f"Seu ticket #{self.ticket_id} foi fechado",
                    description=f"**Título:** {self.ticket_title}\n\n**Motivo do fechamento:**\n{self.reason.value}",
                    color=discord.Color.red()
                )
                dm_embed.set_footer(text=f"Fechado por: {interaction.user.display_name}")
                await ticket_owner.send(embed=dm_embed)
            except discord.Forbidden as e:
                await interaction.followup.send("⚠️ Não foi possível notificar o usuário por DM. (DM fechada ou bloqueada)", ephemeral=True)
                print(f"[ERRO DM] Não foi possível enviar DM para o usuário {self.ticket_owner_id}: {e}")
            except Exception as e:
                await interaction.followup.send(f"⚠️ Erro inesperado ao tentar enviar DM: {e}", ephemeral=True)
                print(f"[ERRO DM] Erro inesperado ao enviar DM para o usuário {self.ticket_owner_id}: {e}")
        else:
            await interaction.channel.send(f"⚠️ Não foi possível notificar o usuário por DM, pois ele não está mais no servidor.")
            print(f"[ERRO DM] Usuário {self.ticket_owner_id} não encontrado no servidor ao fechar ticket.")
        
        # Fechar o ticket
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tickets 
            SET status = "fechado", updated_at = CURRENT_TIMESTAMP, closed_by = ?, closed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (str(interaction.user.id), self.ticket_id))
        conn.commit()
        
        await create_log(self.ticket_id, "FECHADO", interaction.user, f"Motivo: {self.reason.value}")
        
        close_embed = discord.Embed(
            title="🔒 Ticket Fechado",
            description=f"Ticket fechado por {interaction.user.mention}.\n\n**Motivo:** {self.reason.value}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await interaction.channel.send(embed=close_embed)

        log_embed = discord.Embed(
            title="🔒 Ticket Fechado",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        log_embed.add_field(name="📋 ID", value=f"#{self.ticket_id}", inline=True)
        log_embed.add_field(name="👤 Fechado por", value=f"{interaction.user} ({interaction.user.id})", inline=True)
        log_embed.add_field(name="📝 Título", value=self.ticket_title, inline=False)
        log_embed.add_field(name="📄 Motivo", value=self.reason.value, inline=False)
        await send_log_to_channel(interaction.guild, log_embed)
        
        await asyncio.sleep(10)
        await interaction.channel.delete(reason=f"Ticket #{self.ticket_id} fechado")
        
        conn.close()
        await interaction.followup.send("Ticket fechado com sucesso!", ephemeral=True)

@bot.tree.command(name="atribuir", description="Atribui um ticket a um membro da equipe.")
@app_commands.describe(ticket_id="O ID do ticket a ser atribuído.", membro="O membro da equipe para atribuir o ticket.")
async def atribuir_ticket(interaction: discord.Interaction, ticket_id: int, membro: discord.Member):
    if not interaction.user.guild_permissions.administrator: # Simplificado para admin, pode ser trocado por staff
        await interaction.response.send_message("❌ Apenas administradores podem usar este comando.", ephemeral=True)
        return

    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET assigned_to = ? WHERE id = ?", (str(membro.id), ticket_id))
    conn.commit()
    
    cursor.execute("SELECT channel_id FROM tickets WHERE id = ?", (ticket_id,))
    result = cursor.fetchone()
    if result and result[0]:
        channel = interaction.guild.get_channel(int(result[0]))
        if channel:
            await channel.send(f"✅ Este ticket foi atribuído a {membro.mention} por {interaction.user.mention}.")

    conn.close()
    await interaction.response.send_message(f"✅ Ticket #{ticket_id} atribuído a {membro.mention}.", ephemeral=True)

# --- Comandos de Template ---
@bot.tree.command(name="criar-template", description="Cria um novo template de resposta (admin)")
@app_commands.describe(nome="Nome curto para o template (sem espaços).", conteudo="O texto completo da resposta.")
@app_commands.checks.has_permissions(administrator=True)
async def criar_template(interaction: discord.Interaction, nome: str, conteudo: str):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO response_templates (guild_id, name, content) VALUES (?, ?, ?)", (str(interaction.guild.id), nome.lower(), conteudo))
        conn.commit()
        await interaction.response.send_message(f"✅ Template `{nome.lower()}` criado com sucesso!", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message(f"❌ Um template com o nome `{nome.lower()}` já existe.", ephemeral=True)
    finally:
        conn.close()

@bot.tree.command(name="usar-template", description="Usa um template de resposta em um canal de ticket.")
@app_commands.describe(nome="O nome do template a ser usado.")
async def usar_template(interaction: discord.Interaction, nome: str):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM response_templates WHERE guild_id = ? AND name = ?", (str(interaction.guild.id), nome.lower()))
    template = cursor.fetchone()
    conn.close()

    if not template:
        await interaction.response.send_message(f"❌ Template `{nome.lower()}` não encontrado.", ephemeral=True)
        return
    
    # Verifica se é um canal de ticket
    cursor.execute("SELECT id FROM tickets WHERE channel_id = ?", (str(interaction.channel.id),))
    is_ticket_channel = cursor.fetchone()
    if not is_ticket_channel:
        await interaction.response.send_message("❌ Este comando só pode ser usado em um canal de ticket.", ephemeral=True)
        return

    await interaction.response.send_message(template[0])

@bot.tree.command(name="listar-templates", description="Lista todos os templates de resposta disponíveis.")
async def listar_templates(interaction: discord.Interaction):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM response_templates WHERE guild_id = ?", (str(interaction.guild.id),))
    templates = cursor.fetchall()
    conn.close()

    if not templates:
        await interaction.response.send_message("📋 Nenhum template encontrado.", ephemeral=True)
        return
        
    description = "\n".join(f"- `{name[0]}`" for name in templates)
    embed = discord.Embed(title="📋 Templates Disponíveis", description=description, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="deletar-template", description="Deleta um template de resposta (admin)")
@app_commands.describe(nome="O nome do template a ser deletado.")
@app_commands.checks.has_permissions(administrator=True)
async def deletar_template(interaction: discord.Interaction, nome: str):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM response_templates WHERE guild_id = ? AND name = ?", (str(interaction.guild.id), nome.lower()))
    changes = conn.total_changes
    conn.commit()
    conn.close()

    if changes > 0:
        await interaction.response.send_message(f"✅ Template `{nome.lower()}` foi deletado com sucesso.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Template `{nome.lower()}` não encontrado.", ephemeral=True)

@bot.tree.command(name="refresh-bot", description="Recarregar comandos e sincronizar o bot (apenas administradores)")
async def refresh_bot(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você precisa ser administrador para usar este comando.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"🔄 Bot atualizado! {len(synced)} comandos sincronizados.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao atualizar bot: {e}", ephemeral=True)

# --- Comandos de Utilidade ---

@bot.tree.command(name="limpar", description="Limpa um número de mensagens neste canal (apenas staff).")
@app_commands.describe(quantidade="O número de mensagens a serem apagadas (padrão: 10).")
@app_commands.checks.has_permissions(manage_messages=True)
async def limpar(interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100] = 10):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(f"✅ {len(deleted)} mensagens foram apagadas.", ephemeral=True)

@limpar.error
async def limpar_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Ocorreu um erro: {error}", ephemeral=True)

# --- Sistema de Painel de Informações ---

class InfoPanelModal(discord.ui.Modal, title="Configurar Painel de Informações"):
    def __init__(self):
        super().__init__()
        self.name_input = discord.ui.TextInput(
            label="Nome único do painel (para referência)",
            placeholder="Ex: regras, anuncios, etc.",
            required=True
        )
        self.title_input = discord.ui.TextInput(
            label="Título do Embed",
            placeholder="O título que aparecerá no post.",
            required=True
        )
        self.content_input = discord.ui.TextInput(
            label="Conteúdo Principal",
            style=discord.TextStyle.paragraph,
            placeholder="As regras completas, o anúncio, etc.",
            required=True,
            max_length=4000
        )
        self.add_item(self.name_input)
        self.add_item(self.title_input)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO info_panels (guild_id, name, title, content)
            VALUES (?, ?, ?, ?)
        ''', (str(interaction.guild.id), self.name_input.value.lower(), self.title_input.value, self.content_input.value))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ Painel '{self.name_input.value.lower()}' foi configurado com sucesso!\n"
            f"Use `/postar-painel nome:{self.name_input.value.lower()}` para publicá-lo.",
            ephemeral=True
        )

@bot.tree.command(name="criar-painel", description="Cria/edita um painel de informações (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def criar_painel_cmd(interaction: discord.Interaction):
    modal = InfoPanelModal()
    await interaction.response.send_modal(modal)

@criar_painel_cmd.error
async def criar_painel_cmd_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Apenas administradores podem usar este comando.", ephemeral=True)

@bot.tree.command(name="postar-painel", description="Posta um painel de informações em um canal (admin).")
@app_commands.describe(nome="O nome único do painel que você criou.")
@app_commands.checks.has_permissions(administrator=True)
async def postar_painel(interaction: discord.Interaction, nome: str):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, content FROM info_panels WHERE guild_id = ? AND name = ?", (str(interaction.guild.id), nome.lower()))
    panel = cursor.fetchone()
    conn.close()

    if not panel:
        await interaction.response.send_message(f"❌ Painel com o nome '{nome}' não encontrado. Use `/criar-painel` primeiro.", ephemeral=True)
        return

    title, content = panel
    embed = discord.Embed(title=title, description=content, color=discord.Color.blue())
    
    await interaction.response.send_message(embed=embed)

@postar_painel.error
async def postar_painel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Apenas administradores podem usar este comando.", ephemeral=True)

# --- Comandos de Sugestão ---
@bot.tree.command(name="config-sugestoes", description="Configura os canais para o sistema de sugestões (admin).")
@app_commands.describe(canal_sugestoes="O canal onde os membros enviarão sugestões.", canal_aprovadas="O canal para onde as sugestões aprovadas serão enviadas.")
@app_commands.checks.has_permissions(administrator=True)
async def config_sugestoes(interaction: discord.Interaction, canal_sugestoes: discord.TextChannel, canal_aprovadas: discord.TextChannel):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bot_config (guild_id, suggestion_channel_id, approved_suggestion_channel_id) 
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
        suggestion_channel_id = excluded.suggestion_channel_id,
        approved_suggestion_channel_id = excluded.approved_suggestion_channel_id
    ''', (str(interaction.guild.id), str(canal_sugestoes.id), str(canal_aprovadas.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Canais de sugestão configurados com sucesso!\nSugestões em: {canal_sugestoes.mention}\nAprovadas em: {canal_aprovadas.mention}", ephemeral=True)

@bot.tree.command(name="aprovar-sugestao", description="Aprova uma sugestão e a envia para o canal de aprovadas (admin).")
@app_commands.describe(id_sugestao="O ID da mensagem original da sugestão.")
@app_commands.checks.has_permissions(administrator=True)
async def aprovar_sugestao(interaction: discord.Interaction, id_sugestao: str):
    await interaction.response.defer(ephemeral=True)

    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT suggestion_channel_id, approved_suggestion_channel_id FROM bot_config WHERE guild_id = ?", (str(interaction.guild.id),))
    config = cursor.fetchone()
    conn.close()

    if not config or not config[0] or not config[1]:
        await interaction.followup.send("❌ Os canais de sugestão não foram configurados. Use `/config-sugestoes`.", ephemeral=True)
        return

    suggestion_channel_id, approved_channel_id = int(config[0]), int(config[1])
    
    try:
        suggestion_channel = interaction.guild.get_channel(suggestion_channel_id)
        # Tenta encontrar a mensagem pelo ID no rodapé do embed
        async for message in suggestion_channel.history(limit=200):
            if message.embeds:
                embed = message.embeds[0]
                if embed.footer and embed.footer.text == f"ID da Sugestão: {id_sugestao}":
                    original_suggestion_message = message
                    break
        else: # Se o loop terminar sem 'break'
            await interaction.followup.send("❌ Sugestão não encontrada com este ID. Verifique o ID no rodapé da sugestão.", ephemeral=True)
            return

        approved_channel = interaction.guild.get_channel(approved_channel_id)

        # Novo embed para o canal de aprovadas
        approved_embed = original_suggestion_message.embeds[0].copy()
        approved_embed.color = discord.Color.green()
        approved_embed.set_footer(text="Sugestão Aprovada")
        approved_embed.set_author(name=f"Sugestão Aprovada de {approved_embed.author.name}", icon_url=approved_embed.author.icon_url)
        await approved_channel.send(embed=approved_embed)

        # Edita o embed original
        original_embed = original_suggestion_message.embeds[0].copy()
        original_embed.color = discord.Color.green()
        original_embed.title = "✅ SUGESTÃO APROVADA"
        await original_suggestion_message.edit(embed=original_embed, view=None) # Remove botões/views se houver

        await interaction.followup.send("✅ Sugestão aprovada com sucesso!", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Ocorreu um erro: {e}", ephemeral=True)

# --- Comandos de Notificação de Live ---
@bot.tree.command(name="config-live", description="Configura o anúncio de live para um membro (admin).")
@app_commands.describe(streamer="O membro que será monitorado.", canal_anuncio="O canal onde o anúncio será enviado.", mensagem="Mensagem customizada. Use {streamer} e {url}.")
@app_commands.checks.has_permissions(administrator=True)
async def config_live(interaction: discord.Interaction, streamer: discord.Member, canal_anuncio: discord.TextChannel, mensagem: str = None):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO stream_notifications (guild_id, streamer_id, channel_id, custom_message) VALUES (?, ?, ?, ?)
        ON CONFLICT(streamer_id) DO UPDATE SET
        channel_id = excluded.channel_id,
        custom_message = excluded.custom_message
    ''', (str(interaction.guild.id), str(streamer.id), str(canal_anuncio.id), mensagem))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Anúncios de live configurados para {streamer.mention} no canal {canal_anuncio.mention}.", ephemeral=True)

@bot.tree.command(name="remover-live", description="Para de anunciar as lives de um membro (admin).")
@app_commands.describe(streamer="O membro para remover da monitorização.")
@app_commands.checks.has_permissions(administrator=True)
async def remover_live(interaction: discord.Interaction, streamer: discord.Member):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stream_notifications WHERE streamer_id = ?", (str(streamer.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ {streamer.mention} não será mais anunciado.", ephemeral=True)

@bot.event
async def on_presence_update(before, after):
    if before.bot:
        return

    # Detectar se o usuário começou a streamar
    is_streaming_before = any(isinstance(a, discord.Streaming) for a in before.activities)
    is_streaming_after = any(isinstance(a, discord.Streaming) for a in after.activities)

    if not is_streaming_before and is_streaming_after:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, custom_message FROM stream_notifications WHERE streamer_id = ?", (str(after.id),))
        config = cursor.fetchone()
        conn.close()

        if config:
            channel_id, custom_message = config
            streaming_activity = next((a for a in after.activities if isinstance(a, discord.Streaming)), None)

            if streaming_activity and streaming_activity.url:
                channel = after.guild.get_channel(int(channel_id))
                if channel:
                    # Mensagem padrão
                    content = f"🔴 **{after.mention} está ao vivo!**\nVenha assistir: {streaming_activity.url}"
                    # Mensagem customizada
                    if custom_message:
                        content = custom_message.format(streamer=after.mention, url=streaming_activity.url)
                    
                    embed = discord.Embed(
                        title=f"{streaming_activity.name}",
                        description=f"{streaming_activity.details if streaming_activity.details else ''}",
                        url=streaming_activity.url,
                        color=discord.Color.purple()
                    )
                    embed.set_author(name=f"{after.display_name} começou a transmitir", icon_url=after.display_avatar.url)
                    embed.set_thumbnail(url=after.display_avatar.url)
                    
                    try:
                        await channel.send(content, embed=embed)
                    except Exception as e:
                        print(f"Erro ao anunciar live: {e}")

@bot.tree.command(name="live-tiktok", description="Anuncia manualmente uma live do TikTok.")
@app_commands.describe(link="O link da sua live no TikTok.", titulo="O título da sua live (opcional).")
async def live_tiktok(interaction: discord.Interaction, link: str, titulo: str = None):
    # Encontrar o canal de anúncio configurado para qualquer streamer (lógica pode ser melhorada)
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM stream_notifications WHERE guild_id = ? LIMIT 1", (str(interaction.guild.id),))
    config = cursor.fetchone()
    conn.close()

    if not config:
        await interaction.response.send_message("❌ O canal de anúncio de lives ainda não foi configurado. Use `/config-live` primeiro.", ephemeral=True)
        return

    channel_id = config[0]
    channel = interaction.guild.get_channel(int(channel_id))

    if not channel:
        await interaction.response.send_message("❌ O canal de anúncio configurado não foi encontrado.", ephemeral=True)
        return

    if "tiktok.com" not in link:
        await interaction.response.send_message("❌ Por favor, forneça um link válido do TikTok.", ephemeral=True)
        return

    embed = discord.Embed(
        title=titulo or f"Live no TikTok!",
        description=f"**{interaction.user.mention} está ao vivo no TikTok!**\n\n[Clique aqui para assistir!]({link})",
        color=discord.Color.from_rgb(0, 242, 234) # Cor aproximada do TikTok
    )
    embed.set_author(name=f"{interaction.user.display_name} iniciou uma transmissão!", icon_url=interaction.user.display_avatar.url)
    embed.set_thumbnail(url="https://sf-static.tiktokcdn.com/obj/eden-sg/uYVsz-uspq-c/tiktok-icon2.png")

    try:
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Sua live no TikTok foi anunciada com sucesso!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao anunciar a live: {e}", ephemeral=True)
        print(f"Erro ao anunciar live no TikTok: {e}")

class TicketQueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pegar próximo ticket", style=discord.ButtonStyle.success, emoji="🎫")
    async def pegar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild):
            await interaction.response.send_message("❌ Apenas administradores podem pegar tickets da fila.", ephemeral=True)
            return
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ticket_queue ORDER BY created_at ASC LIMIT 1')
        ticket_data = cursor.fetchone()
        if not ticket_data:
            await interaction.response.send_message("📋 Não há tickets na fila de espera.", ephemeral=True)
            conn.close()
            return
        queue_id, user_id, username, category, title, description, created_at = ticket_data
        # Remover da fila
        cursor.execute('DELETE FROM ticket_queue WHERE id = ?', (queue_id,))
        conn.commit()
        # Criar canal de ticket
        category_obj = await get_or_create_ticket_category(interaction.guild)
        channel_names = {
            "ticket_geral": "ticket-geral",
            "denuncia": "denuncia",
            "recrutamento": "recrutamento",
            "suporte_tecnico": "suporte-tecnico",
        }
        channel_name = f"{channel_names.get(category, 'ticket')}-{username}".lower()
        ticket_owner = interaction.guild.get_member(int(user_id))
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }
        if ticket_owner:
            overwrites[ticket_owner] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        else:
            await interaction.response.send_message(f"⚠️ O usuário que abriu o ticket não está mais no servidor. O canal será criado apenas para a equipe.", ephemeral=True)
        ticket_channel = await category_obj.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )
        # Registrar no banco de tickets
        cursor.execute('''
            INSERT INTO tickets (user_id, username, category, title, description, channel_id, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(user_id),
            username,
            category,
            title,
            description,
            str(ticket_channel.id),
            str(interaction.user.id)
        ))
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        await create_log(ticket_id, "CRIADO", interaction.user, f"Categoria: {category}")
        color_map = {
            "ticket_geral": discord.Color.blue(),
            "denuncia": discord.Color.red(),
            "recrutamento": discord.Color.orange(),
            "suporte_tecnico": discord.Color.purple()
        }
        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_id} - {category}",
            color=color_map.get(category, discord.Color.blue()),
            timestamp=datetime.now()
        )
        ticket_owner = interaction.guild.get_member(int(user_id))
        embed.add_field(name="👤 Usuário", value=ticket_owner.mention if ticket_owner else username, inline=True)
        embed.add_field(name="📂 Categoria", value=category, inline=True)
        embed.add_field(name="🔄 Status", value="🟢 Aberto", inline=True)
        embed.add_field(name="📝 Título", value=title, inline=False)
        embed.add_field(name="📄 Descrição", value=description, inline=False)
        embed.add_field(name="👨‍💻 Atendente", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Ticket retirado da fila de espera")
        await ticket_channel.send(f"👋 Olá {ticket_owner.mention if ticket_owner else username}! Seu ticket está sendo atendido por {interaction.user.mention}.", embed=embed)
        await interaction.response.send_message(f"✅ Ticket #{ticket_id} atribuído a você e canal criado: {ticket_channel.mention}", ephemeral=True)

@bot.tree.command(name="postar-fila-tickets", description="Define o canal onde as notificações de tickets em espera serão enviadas.")
@app_commands.describe(canal="Canal onde as notificações serão postadas.")
@app_commands.checks.has_permissions(administrator=True)
async def postar_fila_tickets(interaction: discord.Interaction, canal: discord.TextChannel):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT ticket_category_id, log_channel_id, staff_role_id FROM bot_config WHERE guild_id = ?', (str(interaction.guild.id),))
    row = cursor.fetchone()
    ticket_category_id = row[0] if row else None
    log_channel_id = row[1] if row else None
    staff_role_id = row[2] if row else None
    cursor.execute('''
        INSERT OR REPLACE INTO bot_config (guild_id, ticket_category_id, log_channel_id, staff_role_id, fila_channel_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        str(interaction.guild.id),
        ticket_category_id,
        log_channel_id,
        staff_role_id,
        str(canal.id)
    ))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Canal de fila de tickets configurado para {canal.mention}", ephemeral=True)

# Inicializar banco de dados
init_database()

if __name__ == "__main__":
    try:
        print("🚀 Iniciando bot...")
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ ERRO: Token inválido!")
    except Exception as e:
        print(f"❌ ERRO: {e}")

