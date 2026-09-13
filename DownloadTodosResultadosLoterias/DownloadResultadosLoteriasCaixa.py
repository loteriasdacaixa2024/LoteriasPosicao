
import requests
import os

# Lista de URLs dos arquivos para download
urls = [
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Lotofacil',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Dia-de-Sorte',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Lotomania',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Quina',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Mega-Sena',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Mais-Milionaria',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Dupla-Sena',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Timemania',
    'https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Super-Sete',
]

# Definir o diretório de destino na pasta Downloads do usuário
dest_dir = os.path.join(os.path.expanduser('~'), 'Downloads')


# Iterar sobre a lista de URLs e fazer o download de cada arquivo
for url in urls:
    # Fazer uma requisição GET para a URL
    response = requests.get(url)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Tentar extrair o nome do arquivo a partir do cabeçalho Content-Disposition
        content_disposition = response.headers.get('content-disposition')
        if content_disposition:
            # Exemplo de valor Content-Disposition: 'attachment; filename="resultados_mega_sena.zip"'
            file_name = content_disposition.split('filename=')[-1].strip('"')
        else:
            # Se não houver cabeçalho Content-Disposition, usar um nome padrão baseado na URL
            file_name = url.split('modalidade=')[-1] + '.zip'
        
        # Criar o caminho completo para o arquivo
        file_path = os.path.join(dest_dir, file_name)

        # Salvar o conteúdo da resposta em um arquivo local
        with open(file_path, 'wb') as file:
            file.write(response.content)
        
        print(f"Download concluído com sucesso! Arquivo salvo como {file_name}.")
    else:
        print(f"Erro ao fazer download de {url}. Código de status: {response.status_code}")
