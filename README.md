# Gerador de Relatórios de Visita Rural

Sistema em Python para gerar relatórios de visita rural em Excel a partir de anotações brutas, preservando o arquivo modelo original.

## O que o sistema faz

- Lê anotações brutas do usuário.
- Separa cliente, município/UF, propriedade, áreas, atividades, pecuária, piscicultura, culturas/forrageiras, benfeitorias, máquinas, comentários técnicos e conclusão.
- Converte alqueire goiano/mineiro para hectares usando `1 alqueire = 4,84 ha`.
- Calcula Área de Cultivo somente quando Área Total e Área de Pastagens forem informadas.
- Preenche uma cópia do modelo `.xlsx` com `openpyxl`.
- Insere fotos enviadas pela interface na área de registro fotográfico da planilha.
- Usa `config/cell_map.yaml` para localizar os campos do modelo.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

## Interface

```powershell
python -m streamlit run app.py --server.port 8501
```

Depois acesse:

```text
http://localhost:8501
```

Fluxo da tela:

1. Envie o arquivo modelo `.xlsx`, se a tela pedir.
2. Cole as anotações.
3. Clique em `Analisar`.
4. Confira resumo e avisos.
5. Faça upload das fotos, se houver.
6. Clique em `Gerar relatório`.
7. Baixe o Excel final.

## Publicar para outra pessoa usar

O caminho mais simples é Streamlit Community Cloud:

1. Acesse `https://streamlit.io/cloud`.
2. Conecte sua conta GitHub.
3. Escolha o repositório, a branch `main` e o arquivo principal `app.py`.
4. Clique em `Deploy`.
5. Ao abrir o app, envie o arquivo `RELATÓRIO DE VISITA - MODELO.xlsx` se ele for solicitado na tela.

Para dados sensíveis, prefira repositório privado e app privado. Depois convide seu amigo pelo botão `Share` do Streamlit.

## CLI

A CLI continua disponível para gerar relatório sem fotos:

```powershell
python -m relatorios_rurais.cli generate `
  --model "RELATÓRIO DE VISITA - MODELO.xlsx" `
  --notes-file "anotacoes.txt"
```

## Regras conservadoras

O parser não inventa dados. Quando a anotação não informa um campo, o sistema preenche conforme o mapa:

- texto obrigatório: `Não informado`;
- máquina/equipamento sem dados: `Descrição: Não informado; Fabricante: -; Modelo: -`;
- campo numérico opcional: vazio.
