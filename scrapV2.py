import requests
from bs4 import BeautifulSoup
from pprint import pprint
from datetime import datetime, date
from dateutil.tz import tzutc, gettz # type: ignore

def info_lmu():
    url= 'https://www.racecontrol.gg/'
    fonte = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64'
            'AppleWebKit/537.36 (KHTML, like Gecko)'
            'Chrome/58.0.3029.110 Safari/537.3'
        )
     }
    
    try: 
        response = requests.get(url, headers=fonte)
        response.raise_for_status()

        conteudo = BeautifulSoup(response.content, 'html.parser')

        # Div Principal daily races
        list_daily = conteudo.find('section', class_='mb-5')

        if not list_daily:
            print("DIV nao encontrada")
            return 
        
        #encontrar rank
        ranks= list_daily.find_all('div', class_='position-absolute top-0 start-0 mt-2 ms-2')

        if not ranks:
            print("nada encontrado rank")
            return

        #Encontrar as corridas
        race_info = list_daily.find_all('div', class_='race-info')

        if not race_info:
            print("Nada encontrado em race-info")
            return
                
        corridas_diarias = [] #lista vazia para depois atribuir valor
        

        #ZIP em python ajuda a poder ir buscar valores a mais que uma div, neste caso tinha varias div
        #assim posso usar duas div diferenets no mesmo loop
        for item, rank in zip(race_info, ranks):
            #Nome de corrida 
            nome_corrida = item.find('h4', class_='text-white fs-xl mb-2')
            nome_corrida = nome_corrida.text.strip() if nome_corrida else 'N/A'

            '''trocas_corrida={
                "LMGTE Fixed": "LmGT3 Fixed",
                "LMGT3 Fixed": "LmGTE Fixed"
            }
            novo_nome= nome_corrida
            for antigo, novo in trocas_corrida.items():
                novo_nome = novo_nome.replace(antigo, novo)'''

            #Rank de cada corrida
            rank_name_span= rank.find('span', class_='badge tier-badge')
            rank_name= rank_name_span.text.strip()if rank_name_span else 'NA' 

            ## fazer o replace seguid novos_ranks = rank_name.replace("advanced", "platina").replace("beginner", "bronze")
            #ou criar um dicionario

            trocas= {
                "beginner": ":third_place:Bronze",
                "intermediate":":second_place:Silver",
                "advanced": ":first_place:Gold"
            }
            #esq=chave dir= valor

            novos_ranks=rank_name
            for antigo, novo in trocas.items(): #.item é o uma ação do python para correr dicionairios em for
                novos_ranks= novos_ranks.replace(antigo, novo) #declaro que a chave vai ser trocada pelo valor 
            
            

            #Lop para encontrar o valor da pista e duração,
            #para a pista e duração a div e span tem o mesmo nome/identificador entao 
            #Loop procura duas div com o mesmo nome e que tenham dois span, e se o primeiro span bater o valor no if (duration) o segunda span vai ser o valor dado

            #encontrar todas as divs da pagina com o fonte no incio headers
            fonte = item.find_all('div', class_='race_header d-flex justify-content-between align-items-center mb-1')

            #setup do valor de duracao e pista para default N/A para ser alterado depois

            duracao = pista = 'N/A'

            for divs in fonte:
                spans= divs.find_all('span')
                if len(spans) >= 2:
                    label = spans[0].text.strip().lower() #primeio span encontrado na div, retira espaços e deixa em pequeno
                    valor = spans[1].text.strip()
                    if 'duration' in label:
                        duracao = valor
                    elif 'track' in label:
                        pista = valor
            
            #horarios das corridas, encontrar os diferentes spans para cada horairo 
            horarios_div = item.find('div', class_='mt-2 me-n3')
            horarios_dc = [] #lista vazia para depois atribuir 
            if horarios_div:
                horarios_spans=horarios_div.find_all('span')
                for span in horarios_spans:
                    horario_12h = span.text.strip().split()[-1] #retira os espaços da frase dos horarios e vai buscar o ultimo grupo sendo esse a hora com o -1

                    try:
                        #trasnfomrar a string em um objeto de tempo
                        temp_obj = datetime.strptime(horario_12h, '%I:%M%p').time() #.time so para extrair o time sem a data

                        #Combinar hora com a hora de hoje para assumir que as corridas sao hoje
                        hoje = date.today()
                        temp_obj_completo= datetime.combine(hoje, temp_obj)

                        # transformar o time em UTC defautl
                        temp_utc= temp_obj_completo.replace(tzinfo=tzutc())

                        #Obter timestamp em formato unix para o discor em float
                        unix_float=temp_utc.timestamp()

                        #guardar e transfomrar o float em int inteiro
                        horarios_dc.append(int(unix_float))

                    except ValueError:
                        #se falhar vai guardar o valor original 
                        horarios_dc.append(horario_12h)

           

            detalhes_corrida = {
                'horarios': horarios_dc,
                'nome corrida': nome_corrida,
                'pista': pista,
                'duracao': duracao,
                'rank': novos_ranks
            } #detalhes da lista 

            corridas_diarias.append(detalhes_corrida)

        return {'corridas diaris ':corridas_diarias}

    except requests.exceptions.RequestException as error: #as error → guarda o erro dentro da variável error
        return f"erro load pagina: {error}"  #return f""" string com uma varialvel sendo esssa o erro 
    
if __name__ =="__main__":
    dados_corrida = info_lmu()
    pprint(dados_corrida)
