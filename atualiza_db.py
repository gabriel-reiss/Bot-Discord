import sqlite3

conn = sqlite3.connect('tickets.db')
cursor = conn.cursor()

# Verifica se a coluna já existe
cursor.execute("PRAGMA table_info(bot_config)")
columns = [col[1] for col in cursor.fetchall()]

if 'fila_channel_id' not in columns:
    try:
        cursor.execute('ALTER TABLE bot_config ADD COLUMN fila_channel_id TEXT;')
        print('Coluna fila_channel_id adicionada com sucesso!')
    except Exception as e:
        print(f'Erro ao adicionar coluna: {e}')
else:
    print('A coluna fila_channel_id já existe.')

# Mostrar o valor atual salvo no banco
try:
    cursor.execute('SELECT guild_id, fila_channel_id FROM bot_config')
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f'Guild: {row[0]} | fila_channel_id: {row[1]}')
    else:
        print('Nenhum registro encontrado em bot_config.')
except Exception as e:
    print(f'Erro ao consultar bot_config: {e}')

conn.commit()
conn.close() 