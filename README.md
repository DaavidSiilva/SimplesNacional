# Simples Nacional Lib
<img style="text-align:center" alt="image" src="https://github.com/user-attachments/assets/b4a11a93-2f85-431c-86d9-ed0f647f241f" />

Biblioteca e CLI em Python para consulta e atualização da base de dados pública do Simples Nacional (CNPJs).

## Instalação

Para instalar a biblioteca localmente:

```bash
pip install .
```

## Uso via Linha de Comando (CLI)

Após a instalação, o comando `simplesnacional` estará disponível no seu terminal.

### 1. Atualizar a Base de Dados
Antes de realizar consultas, é necessário baixar e atualizar a base de dados local. O comando abaixo verifica se existe uma nova versão no site da Receita Federal e realiza o download e importação se necessário.

```bash
simplesnacional atualizar
```
Este processo pode demorar alguns minutos dependendo da velocidade da internet e do processamento, pois a base é volumosa.

### 2. Verificar Status
Para ver informações sobre a base de dados local, como a data de referência e o total de registros importados:

```bash
simplesnacional info
```

### 3. Consultar um CNPJ
Para consultar os dados do Simples Nacional de um CNPJ específico:

```bash
simplesnacional consultar 00000000000191
```
Ou com formatação:
```bash
simplesnacional consultar 00.000.000/0001-91
```

**Saída Exemplo:**
```text
Dados do CNPJ: 00000000
+-----------------------+------------+
|                 Campo | Valor      |
+-----------------------+------------+
|         Opção Simples | S          |
|    Data Opção Simples | 20070701   |
| Data Exclusão Simples |            |
|             Opção MEI | N          |
|        Data Opção MEI |            |
|     Data Exclusão MEI |            |
+-----------------------+------------+
```

## Uso como Biblioteca Python

Você pode utilizar a biblioteca diretamente em seu código Python para realizar consultas.

```python
from simplesnacional import consulta

# Realizar a consulta
# O CNPJ pode ser passado como string (com ou sem pontuação) ou inteiro
dados = consulta("00.000.000/0001-91")

if dados:
    print(f"CNPJ Base: {dados.cnpj_base}")
    print(f"Optante Simples: {dados.opcao_simples}")
    print(f"Data Opção: {dados.data_opcao_simples}")
    print(f"Optante MEI: {dados.opcao_mei}")
else:
    print("CNPJ não encontrado na base local.")
```

### Estrutura do Objeto Retornado
A função `consulta` retorna um objeto `DadosSimples` com os seguintes atributos:

- `cnpj_base`: Os 8 primeiros dígitos do CNPJ
- `opcao_simples`: Indicador de opção pelo Simples ('S' ou 'N')
- `data_opcao_simples`: Data da opção pelo Simples
- `data_exclusao_simples`: Data da exclusão do Simples (se houver)
- `opcao_mei`: Indicador de opção pelo MEI ('S' ou 'N')
- `data_opcao_mei`: Data da opção pelo MEI
- `data_exclusao_mei`: Data da exclusão do MEI (se houver)

## Licença

MIT License
