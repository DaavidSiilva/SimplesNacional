import requests
from bs4 import BeautifulSoup
from datetime import datetime
import zipfile 
import os 
import sqlite3
import csv
import argparse
import re
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

class DadosSimples:
    def __init__(self, data):
        self.cnpj_base = data[0]
        self.opcao_simples = data[1]
        self.data_opcao_simples = self._format_date(data[2])
        self.data_exclusao_simples = self._format_date(data[3])
        self.opcao_mei = data[4]
        self.data_opcao_mei = self._format_date(data[5])
        self.data_exclusao_mei = self._format_date(data[6])

    def _format_date(self, date_str):
        if date_str and len(str(date_str)) == 8 and str(date_str).isdigit():
            date_str = str(date_str)
            return f"{date_str[6:8]}/{date_str[4:6]}/{date_str[0:4]}"
        return date_str

    def __repr__(self):
        return f"<DadosSimples(cnpj={self.cnpj_base}, simples={self.opcao_simples}, mei={self.opcao_mei})>"

def get_db_paths():
    target_dir_tmp = os.path.join(os.path.expanduser("~"), ".simples", "tmp")
    db_path = os.path.join(os.path.expanduser("~"), ".simples", "simples.db")
    return target_dir_tmp, db_path

def consulta(cnpj):
    # Limpar CNPJ e pegar os 8 primeiros dígitos
    clean_cnpj = re.sub(r'\D', '', str(cnpj))
    cnpj_base = clean_cnpj[:8]
    
    _, db_path = get_db_paths()
    
    if not os.path.exists(db_path):
        console.print("[red]Banco de dados não encontrado. Execute 'simplesnacional atualizar' primeiro.[/]")
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM SIMPLES WHERE CNPJ_BASE = ?", (cnpj_base,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return DadosSimples(result)
    return None

def info():
    _, db_path = get_db_paths()
    if not os.path.exists(db_path):
        console.print("[red]Banco de dados não encontrado.[/]")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Pegar metadados
    cursor.execute("SELECT DATA_BASE FROM METADATA ORDER BY ROWID DESC LIMIT 1")
    meta = cursor.fetchone()
    data_base = meta[0] if meta else "Desconhecida"
    
    # Contar registros (pode ser lento, usar COUNT *)
    try:
        cursor.execute("SELECT Count(*) FROM SIMPLES")
        count = cursor.fetchone()[0]
    except:
        count = 0
        
    conn.close()
    
    panel = Panel(
        f"Data Base: [bold cyan]{data_base}[/]\n"
        f"Total de CNPJs: [bold green]{count:,}[/]",
        title="Simples Nacional Info"
    )
    console.print(panel)

def db_init():
    _, db_path = get_db_paths()
    target_dir = os.path.dirname(db_path)
    os.makedirs(target_dir, exist_ok=True)
    
    console.print("[cyan]Inicializando banco de dados...[/]")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript('''
        DROP TABLE IF EXISTS SIMPLES;
        DROP TABLE IF EXISTS METADATA;
        CREATE TABLE SIMPLES (
            CNPJ_BASE TEXT PRIMARY KEY,
            OPCAO_SIMPLES TEXT,
            DATA_OPCAO_SIMPLES TEXT,
            DATA_EXCLUSAO_SIMPLES TEXT,
            OPCAO_MEI TEXT,
            DATA_OPCAO_MEI TEXT,
            DATA_EXCLUSAO_MEI TEXT
        );
        CREATE TABLE METADATA (
            DATA_BASE TEXT,
            DATA_DOWNLOAD TEXT            
        );
    ''')
    conn.commit()
    conn.close()
    console.print("[green]Banco de dados recriado.[/]")

def parse_csv(version_date):
    target_dir, db_path = get_db_paths()
    
    # Encontrar arquivo
    try:
        arquivos = os.listdir(target_dir)
        arquivo_nome = [f for f in arquivos if "SIMPLES" in f][0]
        csv_path = os.path.join(target_dir, arquivo_nome)
    except (IndexError, FileNotFoundError):
        console.print("[bold red]Nenhum arquivo CSV 'Simples' encontrado em:[/]")
        console.print(f"[red]{target_dir}[/]")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")
    
    file_size = os.path.getsize(csv_path)
    batch_size = 100000
    batch = []
    
    query = '''
    INSERT OR REPLACE INTO SIMPLES (
        CNPJ_BASE, OPCAO_SIMPLES, DATA_OPCAO_SIMPLES, DATA_EXCLUSAO_SIMPLES,
        OPCAO_MEI, DATA_OPCAO_MEI, DATA_EXCLUSAO_MEI
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    '''

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Importando para o banco de dados...", total=file_size)
        
        with open(csv_path, 'r', encoding='latin-1') as f:
            def file_reader_generator():
                processed_bytes = 0
                last_update = 0
                for line in f:
                    yield line
                    processed_bytes += len(line) + 1 
                    if processed_bytes - last_update > 1024 * 1024: 
                        progress.update(task, completed=processed_bytes)
                        last_update = processed_bytes
                progress.update(task, completed=processed_bytes)

            reader = csv.reader(file_reader_generator(), delimiter=';', quotechar='"')
            for row in reader:
                if len(row) == 7:
                    batch.append(row)
                if len(batch) >= batch_size:
                    cursor.executemany(query, batch)
                    conn.commit()
                    batch = []
            if batch:
                cursor.executemany(query, batch)
                conn.commit()

    console.print("[cyan]Criando índice no banco de dados...[/]")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cnpj_base ON SIMPLES (CNPJ_BASE ASC)")
    conn.commit() 
    
    console.print("[cyan]Atualizando metadados...[/]")
    cursor.execute("INSERT INTO METADATA (DATA_BASE, DATA_DOWNLOAD) VALUES (?, ?)", 
                   (version_date.strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    console.print("[bold green]Importação concluída com sucesso![/]")

    try:
        os.remove(csv_path)
        console.print(f"[green]Arquivo temporário removido: {arquivo_nome}[/]")
    except OSError as e:
        console.print(f"[red]Erro ao remover arquivo temporário: {e}[/]")

def get_local_version():
    _, db_path = get_db_paths()
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DATA_BASE FROM METADATA ORDER BY ROWID DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        if result:
            return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None
    return None

def atualizar():
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        task_check = progress.add_task("[cyan]Verificando atualizações...", total=None)
        
        try:
            url = "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/?C=N;O=D"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")
            
            entries = []
            table = soup.find('table')

            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        date_text = cols[2].get_text(strip=True)
                        if date_text and date_text != '-':
                            try:
                                dt = datetime.strptime(date_text, '%Y-%m-%d %H:%M')
                                link = cols[1].find('a')
                                if link:
                                    href = link.get('href')
                                    if "temp" not in href:
                                        entries.append((dt, href))
                            except ValueError:
                                continue
        except Exception as e:
            progress.update(task_check, completed=True)
            console.print(f"[red]Erro ao conectar com a Receita Federal: {e}[/]")
            return

        progress.update(task_check, completed=True)

        if entries:
            most_recent_date, most_recent_href = max(entries, key=lambda x: x[0])
            local_date = get_local_version()
            
            console.print(Panel(
                f"Data Disponibilização (Site): [bold green]{most_recent_date}[/]\n"
                f"Data Base Local: [bold yellow]{local_date if local_date else 'Inexistente'}[/]", 
                title="Status de Versão"
            ))
            
            if local_date is None or most_recent_date > local_date:
                console.print("[bold green]Nova versão disponível ou banco inexistente. Iniciando atualização...[/]")

                url_zip = f"https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/{most_recent_href}Simples.zip"            
                response = requests.get(url_zip, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                
                if response.status_code == 200:
                    target_dir, _ = get_db_paths()
                    os.makedirs(target_dir, exist_ok=True)
                    zip_path = os.path.join(target_dir, "Simples.zip")

                    task_download = progress.add_task("[green]Baixando arquivo...", total=total_size)
                    
                    with open(zip_path, "wb") as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            file.write(chunk)
                            progress.update(task_download, advance=len(chunk))
                    
                    console.print("[green]Arquivo baixado com sucesso.[/]")

                    task_extract = progress.add_task("[yellow]Descompactando...", total=None)
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(target_dir)
                    progress.update(task_extract, completed=True)
                    
                    console.print(f"[green]Arquivo descompactado com sucesso em: {target_dir}[/]")
                    os.remove(zip_path)
                    console.print("[green]Arquivo removido com sucesso.[/]")
                    
                    db_init()
                    parse_csv(most_recent_date)
                    
                else:
                    console.print(f"[bold red]Erro ao baixar o arquivo. Status code: {response.status_code}[/]")
            else:
                console.print(f"[bold blue]O banco de dados já está atualizado.[/]")
        else:
            console.print("[red]Nenhuma data encontrada no site.[/]")

def cli():
    parser = argparse.ArgumentParser(description="Gestor do Simples Nacional")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando: consultar
    parser_consultar = subparsers.add_parser("consultar", help="Consulta um CNPJ na base de dados")
    parser_consultar.add_argument("cnpj", help="CNPJ para consulta (apenas números ou formatado)")

    # Comando: atualizar
    subparsers.add_parser("atualizar", help="Verifica e atualiza a base de dados")

    # Comando: info
    subparsers.add_parser("info", help="Exibe informações sobre a base de dados local")

    args = parser.parse_args()

    if args.command == "consultar":
        dados = consulta(args.cnpj)
        if dados:
            table = Table(title=f"Dados do CNPJ: {dados.cnpj_base}")
            table.add_column("Campo", justify="right", style="cyan", no_wrap=True)
            table.add_column("Valor", style="magenta")
            
            table.add_row("Opção Simples", dados.opcao_simples)
            table.add_row("Data Opção Simples", dados.data_opcao_simples)
            table.add_row("Data Exclusão Simples", dados.data_exclusao_simples)
            table.add_row("Opção MEI", dados.opcao_mei)
            table.add_row("Data Opção MEI", dados.data_opcao_mei)
            table.add_row("Data Exclusão MEI", dados.data_exclusao_mei)
            
            console.print(table)
        else:
            console.print(f"[red]CNPJ {args.cnpj} não encontrado na base.[/]")

    elif args.command == "atualizar":
        atualizar()

    elif args.command == "info":
        info()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()
