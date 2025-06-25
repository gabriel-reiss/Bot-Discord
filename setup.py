import os
import subprocess
import sys

def install_requirements():
    """Instala as dependências necessárias"""
    print("📦 Instalando dependências...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependências instaladas com sucesso!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Erro ao instalar dependências")
        return False

def create_env_file():
    """Cria arquivo .env se não existir"""
    if not os.path.exists(".env"):
        env_content = """# Configure seu token do Discord aqui
DISCORD_BOT_TOKEN=SEU_TOKEN_AQUI

# Opcional: ID do servidor para comandos específicos
GUILD_ID=ID_DO_SERVIDOR_AQUI
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        print("✅ Arquivo .env criado!")
    else:
        print("✅ Arquivo .env já existe!")

def main():
    print("🤖 CONFIGURADOR DO BOT DE TICKETS DISCORD\n")
    
    # Instalar dependências
    if not install_requirements():
        return
    
    # Criar arquivo .env
    create_env_file()
    
    print("\n" + "="*50)
    print("🎯 PRÓXIMOS PASSOS:")
    print("1. ✅ Dependências instaladas")
    print("2. ✅ Arquivo .env criado")
    print("3. 🔑 Configure seu token no arquivo .env")
    print("4. 🚀 Execute: python bot.py")
    
    print("\n📋 COMO OBTER O TOKEN:")
    print("1. Acesse: https://discord.com/developers/applications")
    print("2. Clique em 'New Application'")
    print("3. Vá para 'Bot' → 'Reset Token'")
    print("4. Copie o token e cole no arquivo .env")
    
    print("\n🔗 COMO ADICIONAR O BOT:")
    print("1. Em 'OAuth2' → 'URL Generator'")
    print("2. Marque: 'bot' e 'applications.commands'")
    print("3. Permissões: 'Send Messages', 'Use Slash Commands', 'Manage Channels'")
    print("4. Use a URL gerada para adicionar ao servidor")
    
    print("\n✨ COMANDOS PRINCIPAIS:")
    print("• /config-bot - Configurar canais e roles")
    print("• /setup-suporte - Criar painel de tickets")
    print("• /stats-tickets - Ver estatísticas")
    print("• /listar-tickets - Listar todos os tickets (staff)")
    print("• /logs-ticket - Ver logs de um ticket")
    print("• /meus-tickets - Ver seus tickets")

if __name__ == "__main__":
    main()
