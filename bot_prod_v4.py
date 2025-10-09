import discord
import os
import json
from dotenv import load_dotenv
from discord.ext import commands, tasks
from datetime import datetime, time, timezone, timedelta
from scrapV2 import info_lmu

load_dotenv()

#Bot token e id do canal 
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

#Funcao para o json e channel id 
def load_config():#load das configs do json
    try:
        with open('config.json', 'r') as f: #r é para read only
            return json.load(f) #função que le e o json e transforma num dicionario em python
    except(FileNotFoundError, json.JSONDecodeError):
        return{}

def save_config(config):
    with open('config.json', 'w') as f: #w abrir em escrever
        json.dump(config, f, indent=4) #faz o processamento do .load, indent para formatar em 4, config é o dicionario onde vai dar save



#BOT

#defenir permissões do bot
perms = discord.Intents.default()
perms.message_content= True
bot= commands.Bot(command_prefix='!', intents=perms)
#bot = discord.Client(intents=perms)


#Racenow comand 
@bot.command()
async def racenow(ctx):
    #envia msg de espera
    msg_espera= await ctx.send("Searsching for new races")
    #chama a funcção do embed
    resultados= await embed_msg()
    #apagar a msg de espera
    await msg_espera.delete()

    #se resutlaod none
    if resultados is None:
        await ctx.send("Nenhuma corrida encontrada")
        return
    
    #Se resultado string, msg de erro do site
    if isinstance(resultados, str):
        await ctx.send(resultados)
        return
    
    #se passou tudo sem erro 
    embed_final= resultados
    await ctx.send(embed=embed_final)


#set chanel command "!setchannel"
@bot.command()
@commands.has_permissions(administrator=True) #so admins conseguem 
async def setchannel(ctx, channel: discord.TextChannel): #declaramos que o o channel vem da funcção do discord.text com o ctx
    config= load_config()
    # chave sera o id do server
    server_id= str(ctx.guild.id) #transforma o id do servidor em string par ao json

    #guaardar o id do servidor associar ao id do cannal
    if server_id not in config:
        config[server_id]={}

    config[server_id]['notification_channel'] = channel.id #notification_channel é a chave para o json

    save_config(config)

    await ctx.send(f"Canal {channel.mention} foi setup")

#erros do commando 
@setchannel.error
async def setchannel_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Mencione o conal. ex: '!serchannel #nome-canal'")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("So adm podem dar set")
    else:
        print(f"erro: {error}")
        await ctx.send("Erro")



#fim do comando 

#função para organizar os ranks.
# linha 169
# corrida vem da função sorted() que pega na lista de corridas e neste caso entre a key/chave get_sort_order
# lista_corridas--> get_sort_order (aqui corrida é uma variavel local) corriga.get vais buscar a lista_corridas
def get_sort_order(corrida):
    #ve o range e returna com o numero 
    #ordem Bronze(0)<silver(1)<gold(2)
    rank_str=corrida.get('rank', '').lower() #transforma o rank em minisculo
    if 'bronze' in rank_str:
        rank_priori=0
    elif 'silver' in rank_str:
        rank_priori=1
    elif 'gold' in rank_str:
        rank_priori=2
    else:
        rank_priori=99 #se nao tiver rank
    
    #rank corrida
    category_str= corrida.get('nome corrida', '').lower()
    if 'lmgt3 fixed' in category_str:
        cat_priori=0
    elif 'lmgte fixed' in category_str:
        cat_priori = 1
    elif 'prototype trophy' in category_str:
        cat_priori = 2
    elif 'elms sprint cup' in category_str:
        cat_priori = 3
    elif 'wec-xperience fixed' in category_str:
        cat_priori = 4
    elif 'super 60 series' in category_str:
        cat_priori = 5
    else:
        cat_priori = 99 #priorida alfabetica para todas as outras 
    
    return (rank_priori, cat_priori)



#criar uma lista/dicionaio para todas as horas certas em UTC
horas_utc = [time(hour=h, tzinfo=timezone.utc)for h in range(24)]

async def embed_msg():
    """esta função vai fazer o scrap e criar um embed fora da função de send_hour_race"""
    print("Executar função embed")
        #2 Start Scraping e verificar erros com msg 
    
    #chamar função lmu
    dados = info_lmu()

    if isinstance(dados, str): #verifica se o scrap devolveu uma string (msg de erro), progamado no scrap para isso 
        print(f"scrap falhou erro: {dados}")

        #enviar msg de erro 
        msg_erro= f"Houve um erro a tentar obter os dados das corridas: ```{dados}```"
        return msg_erro
        
        #for para enviar a msg de erro para todos os canais
    """ for channel in canais_notif:
            try:
                await channel.send(msg_erro)
            except Exception as e:
                print(f"Nao foi possivel enviar msg para o {channel.name}: {e}")
        return #para a tarefa pois nao tem mais nada a fazer, devido ao scrap ter falhado """
    
    #3 se o scrap funcionar e devolver o dicionario e nao uma string 
    #Criar msg e enviar vai acontecer agora 

    #Extrair o dicionario de corridas do scraping (final do codigo) e verificar se tem alguma corrida 
    lista_corridas = dados.get('corridas diaris ', [])
    if not lista_corridas:
        print("Nenhuma corrida encontrada")
        return None

    #vai ordenar a lista de corridas pela nossa ordem defenida em cima// sorted é uma função de python que ordena segunda a chave dada
    lista_ordenada = sorted(lista_corridas, key=get_sort_order)

    #este bloco vai filtrar todas as horas e consoante a hora atula vai mostar na msg as corridas dentro das proximas duas horas
    #definir  msg proximas 2h
    agora_utc=datetime.now(timezone.utc)
    limit_utc= agora_utc + timedelta(minutes=70) #hora atual mais 2h com a funcção de time delta

    #converter para timestap em inteiro para comparar com o scraper 
    agora_ts=int(agora_utc.timestamp())
    limit_ts=int(limit_utc.timestamp())

    #nova lista com apenas os horarios relevantes para as proximas horas
    final_corridas_filtras= []
    for corrida in lista_ordenada:
        #filtrar horarios para cada corida
        horas_validas = []
        for ts in corrida.get('horarios', []):
            #verificar se ts esta dentro do range de 2h
            if isinstance(ts, int) and agora_ts <= ts < limit_ts:
                horas_validas.append(ts)

    #se for encontrado um unico horario valido 
        if horas_validas:
            #criar copia da corrida e atulizamos 
            corrida_filtrada= corrida.copy()
            corrida_filtrada['horarios']= horas_validas
            #adicionar a lista final 
            final_corridas_filtras.append(corrida_filtrada)
    
    #se depois de filtra nao tiver mais corridas dizer para naof azer nada
    if not final_corridas_filtras:
        print("Nenuma corrida encontrada nas proximas 2h")
        return None


    #cria a base do embed para se adicionanda a informação com hora atual
    # Usamos o timestamp da 'hora atual' (agora_ts) para criar um título dinâmico.
    # O flag :f mostra a data e a hora (ex: "18 de setembro de 2025 21:45")
    titulo=f"Corridas Diarias LMU: <t:{agora_ts}:t>"
    msg= discord.Embed(
        title=titulo,
        description="Proximas corridas: ",
        color=discord.Color.red()#muda a cor
    ) 
    msg.set_thumbnail(url="https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2399420/f510badbf573eecdf529ae735a49331f4b9919be/header.jpg?t=1756723410")


    #loop para adicionar os campos no embed ja criado 
    for corrida in final_corridas_filtras: #for corrida faz isto para cada corrida individualmente intera
        
        #extrair todos os dados para variaveis
        rank=corrida.get('rank', 'N/A')
        pista=corrida.get("pista","N/A")
        categoria=corrida.get('nome corrida', "N/A")
        duracao=corrida.get("duracao", "N/A")
        horarios_list=corrida.get("horarios", [])

        #pegar no hoarios_list e trasnformar para timestap do dc
        horario_format=[]
        for ts in horarios_list: #ts varialvel escolhida para o for (loop) guardar o dados
            #verifica primeiro se é um int 
            if isinstance(ts, int):
                #flag :t para mostar apenos horas e min
                horario_format.append(f"<t:{ts}:t>")
            else:
                #se nao foi int o scrap falhou
                horario_format.append(ts)


        #formatar o bloco horarios 
        horarios_str = ' | '.join(horario_format) if horario_format else "N/A"

        #construit o bloco de informação para o embed usando f string
        field_value =(
            f"Safety Rank: **{rank}**  Pista: **{pista}**\n"
            f"Categoria: **{categoria}** Hora: **{horarios_str}**\n"
            f"Duração: **{duracao}**"
        )

        #adiconar as corridas com nova secção ao embed com o field
        msg.add_field(
            name="----------------------------------",
            value=field_value,
            inline=False
        )
    return msg


    


"""Versao V2, evita que o bot falhe o loop de msg e crash se o site estiver down
isto é feito, checking os canais primeiro e so deppois criando o embed, enviado 
uma smg de erro caso o site esteja em baixo nao cancelando o loop"""

"""Versao V3, criara a funcao embed_msg separada do loop da horas, para assim poder chamar a funcao separada,
podendo criar o comando !racenow
setcanal -> setchannel"""

"""V4, envia a msg e guarda o ID da msg, para depois apagar a ultima msg e poder enviar uma nova"""

@tasks.loop(time=horas_utc) #transform a 'send_hour_race' numa tarefa a cada hora que o discord.py vai rodar
#@tasks.loop(seconds=30)
async def send_hour_race():
    print(f"Start task: {datetime.now().strftime('%H:%M:%S')}")

    #Carregar o json
    #config agora contem dicionarions no .json
    config=load_config()
    print("[Debug] Deleting old Msg")

    #percore no json se tem um server_id ou um server_config
    for server_id, server_config in config.items():
        print("[DEBUG] check server id: {server_id}")

        #vererifica se tem alguma msg 
        if 'last_message_id' in server_config:
            print("[DEBU] 'last_message_id' para o servidor {server_id}")
            #se tiver pegamos na informação e guardamos em variaveis novas
            channel_id=server_config.get('notif_channel')
            msg_id=server_config.get('last_message_id')

            #verifica se tem mais uma vez se nao continua para o proximo server
            if not channel_id or not msg_id:
                print("[DEBUG] channel_id missing for {server_id}. Skiping")
                continue

            print("[DEBUG]Preparar para apagar {msg_id} no canal {channel_id}")
            #encontrar o canal e tentar apagar a msg
            #try para evitar erros:
            try:
                print("[DEBUG] 1. Trying fetch")
                #funcção que faz conexão a api do discord com a fução para ir buscar a o ID da msg enviada
                channel= await bot.fetch_channel(channel_id)

                print("[DEBUG]2. canal {channel.name} trying fetch")
                old_msg= await channel.fetch_message(msg_id)

                print("[DEBUG] 3. msg encontrada")
                #se encontrada apagamos
                await old_msg.delete()
                print(f"Msg apagada {msg_id}")
                #apagar o last msg id para evitar que se tenta apgar depois outra vez e nao sobrecarregar o json
                del config [server_id]['last_message_id']
                
                # Só apagamos a referência SE a mensagem foi apagada com sucesso.
                if 'last_message_id' in config.get(server_id, {}):
                    del config[server_id]['last_message_id']
                    print(f"[DEBUG] Referência do ID {msg_id} removida do config.")
                #se por algum motivo a msg ja foi apagada ou nao ecnontrada o expept evita erros e continua
                
            except discord.NotFound:
                print(f"Msg antiga nao encontrada {msg_id}")

                # Se não foi encontrada, a mensagem já não existe, por isso podemos limpar a referência.
                if 'last_message_id' in config.get(server_id, {}):
                    del config[server_id]['last_message_id']
                #se o bot nao tiver perms return a error 
            except discord.Forbidden:
                print(f"Sem permissoes par ao canal {channel_id}")
                
                #se tiver mais algum erro
            except Exception as e:
                print(f"Err: {e}")
                
        
    #guardar tudo dnv no ficheiro json
    save_config(config)

    #chamar a nova funcao do embed que agora esta separada
    resultado= await embed_msg()

    if resultado is None:
        print("Sem resultado a mostrar")
        return
    
    #Se o resultado for um string, quer dizer que é uma msg de erro e algo falhou 
    if isinstance(resultado, str):
        msg=resultado
    else:
        msg= resultado
    


    #reload do json para o mais recente
    config= load_config()
    canais_notif = [] #dicionario para os canais 

    #interar todos os servidores para enviar 
    for guild in bot.guilds:
        #funcção do discodr.py para verificar todos os server.id
        server_id= str(guild.id)
        #verificar se o servidor esta no ficheiro 
        if server_id in config and 'notification_channel' in config[server_id]:
             #obter o channel id do json
            channel_id= config[server_id]['notification_channel']
            #funcção que pega o id e devolve em objeto para poder enviar msg
            channel = bot.get_channel(channel_id)
            #adicona no dicionario canais_notif todos os canis que foram encontrados
            if channel:
                canais_notif.append(channel)
            else:
                print(f"Canal {channel_id} nao encontrado no servidor {guild.name} ")
    
    #se nao tiver nenhum canal e sv config nao precisa fazer o scrap
    if not canais_notif:
        print("Nenhum canal configed")
        return #teste
    
    #4. enviar a msg para os canais encontrados 
    for channel in canais_notif:
        server_id=str(channel.guild.id)
        try:
            #envia a msg (embed ou msg de erro) para o canal e guarda na nova variavel
            if isinstance(msg, discord.Embed):
                nova_msg= await channel.send(embed=msg)
            else:
                nova_msg= await channel.send(msg)

            if server_id not in config:
                config[server_id]={}
            config[server_id]['last_message_id']= nova_msg.id

            print(f"msg enviada para: {channel.guild.name}-> {channel.name}")
        except Exception as e:
            print(f"Erro ao enviar para {channel.name}: {e}")

    save_config(config)
    print("MSg enviada para todos")

#Evento chamado quando o bot conecta com o discord 
#iniciar tarefa de loop
@bot.event
async def on_ready():
    print(f"Bot ligado com {bot.user}")
    #iniciar loop
    send_hour_race.start()

bot.run(BOT_TOKEN)



    
