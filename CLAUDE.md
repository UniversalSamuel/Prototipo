# Assistente de Gestão de Atividades — P&D Univel

## O que essa automação faz

Samuel (coordenador do P&D) registra solicitações de atividade para colaboradores da
equipe por voz. Este arquivo orienta o Claude Code sobre como conduzir esse fluxo do
início ao fim.

## Fluxo passo a passo

### 0. Início de cada sessão (nesta ordem)

**0a. Checagem periódica (até 4x por dia, em horário comercial)**
- Horários-alvo: 08:00, 10:40, 13:20, 16:00.
- Ler o arquivo `.ultima_checagem.txt` na raiz do projeto (guarda a data/hora da
  última checagem; se não existir, tratar como "nunca rodou").
- Calcular qual foi o último horário-alvo de hoje que já passou (ex: se agora são
  14:10, o último horário-alvo que já passou é 13:20).
- Se `.ultima_checagem.txt` já tiver uma data/hora igual ou depois desse
  horário-alvo, pular esta etapa (já rodou para esse horário) e ir direto para 0b.
- Caso contrário, executar o passo 6 (checagem periódica) descrito mais abaixo, e
  depois gravar a data/hora atual em `.ultima_checagem.txt`.
- Isso existe porque a tarefa agendada do Windows só abre a janela do app nesses 4
  horários — quem efetivamente dispara a checagem é o início desta sessão, não um
  processo invisível separado. Se Samuel abrir o app fora desses horários, a
  checagem roda na primeira sessão depois de cada horário-alvo vencido, e só uma
  vez por horário (não fica repetindo a cada mensagem).

**0b. Lista diária de tarefas por colaborador (1x por dia, junto do horário das 08:00)**
- Ler o arquivo `.ultima_lista_diaria.txt` na raiz do projeto (guarda só a data; se
  não existir, tratar como "nunca rodou").
- Se a data nele registrada já for a de hoje, pular esta etapa e ir direto para 0c.
- Se agora ainda for antes das 08:00, também pular (só dispara depois desse
  horário) e ir direto para 0c.
- Caso contrário, executar o passo 7 (lista diária de tarefas por colaborador)
  descrito mais abaixo, e depois gravar a data de hoje em
  `.ultima_lista_diaria.txt`.

**0c. Processamento de pendências de anotação (áudio e texto)**
- Verificar as pastas `pendentes/` (áudio) e `pendentes_texto/` (texto digitado no
  Painel) dentro do projeto.
- Juntar os itens das duas pastas numa única fila, ordenada cronologicamente pelo
  nome do arquivo (timestamp), do mais antigo para o mais novo, e processar **cada
  um**, seguindo os passos 1 a 4 abaixo para cada item.
- Para `.wav`: transcrever rodando `python transcrever.py "pendentes\NOME.wav"`
  (script local, offline, usa faster-whisper — primeira execução do dia pode
  demorar um pouco mais para carregar o modelo). Nunca pular a transcrição nem
  inventar o conteúdo a partir do nome/horário do arquivo.
- Para `.txt`: ler o conteúdo do arquivo diretamente como se fosse a transcrição —
  já é texto, não precisa de transcrição.
- Se o conteúdo (transcrito ou digitado) sair curto, ambíguo ou parecer teste/ruído
  (ex: contagem, frase incompleta sem colaborador identificável), perguntar a
  Samuel antes de assumir que é uma atividade real ou descartar.
- Após processar um item com sucesso (registro criado e mensagem enviada, ou
  descartado a pedido de Samuel): mover `.wav` de `pendentes/` para `processados/`;
  apagar o `.txt` de `pendentes_texto/` (não precisa manter histórico do arquivo de
  texto bruto — o registro fica no banco). Nunca apagar `.wav` sem passar por
  `processados/` primeiro.
- Se não houver nenhum item pendente em nenhuma das duas pastas, informar
  brevemente e seguir para o restante da conversa normalmente.
- A captura acontece pelo **Painel de Gestão à Vista** (`dashboard.py`, ver seção
  própria abaixo) — botão de gravação ou caixa de texto. Nenhum dos dois faz
  classificação, registro ou envio; só capturam e enfileiram. Não assumir que o
  conteúdo já foi processado; todo item encontrado é novo.

### 1. Captura da anotação
- Samuel fala a atividade e para quem é (ex: "pede pro Alexandre revisar o FAP do
  item X até essa semana, é urgente").
- Transcreva a fala e extraia: colaborador, descrição da atividade, e qualquer pista
  de prazo/urgência já mencionada.
- **Samuel também pode definir o prazo diretamente**, em vez de pedir pro
  colaborador informar um (ex: "prazo é dia 10/08", "até sexta que vem", "coloca
  prazo pra amanhã"). Diferencie isso de urgência vaga (palavras como "urgente"
  sozinhas não são um prazo — só disparam a classificação do passo 2). Se tiver
  uma data concreta dita pelo próprio Samuel, trate como prazo já definido — ver
  ajuste no passo 3 e 4 abaixo.
- **Identifique se é atividade nova ou atualização de uma já existente.** Se a
  anotação soar como "define/muda o prazo de [algo que já foi pedido]" em vez de
  um pedido novo, procure no banco um registro em aberto (status ≠ "Concluído")
  com colaborador e título parecidos antes de criar um novo. Se achar um único
  candidato claro, é uma atualização (pular os passos 2–4, ir direto para a lógica
  de "Samuel define prazo em atividade existente" descrita no passo 5). Se houver
  mais de um candidato possível ou nenhum, perguntar a Samuel qual atividade é
  antes de agir — nunca adivinhar.

### 2. Classificação de urgência (SEMPRE confirmar, nunca decidir sozinho)
- Avalie se o conteúdo soa urgente (expressões como "urgente", "pra ontem", "o mais
  rápido possível", "prioridade máxima", ou variações equivalentes em contexto).
- **Desde 10/08/2026: urgente também vai por Outlook**, não por Teams — decisão de
  Samuel, porque o Teams não tem como enviar sem a janela em primeiro plano (ver
  seção "Como enviar mensagens"), o que quebraria a captura instantânea por voz
  pras atividades urgentes. Urgência agora afeta o **e-mail em si** (prefixo
  "URGENTE" no assunto + importância alta), não o canal.
- Pergunte a Samuel explicitamente antes de enviar, por exemplo:
  - Se detectou urgência: "Detectei urgência nessa solicitação — confirmo o envio
    por Outlook, marcado como urgente?"
  - Se não detectou: "Não detectei urgência — confirmo o envio por Outlook?"
- Só prossiga após a confirmação de Samuel. Se ele pedir Teams explicitamente
  mesmo assim, avisar que esse envio não é automático (precisa dele na tela pra
  automação de tela funcionar) antes de prosseguir.

### 3. Registro no banco de dados local (SQLite)
- Banco: `atividades_pd.db` (caminho definido na seção de configuração abaixo)
- Tabela: `atividades_pd`
- Criar um novo registro com:
  - titulo: descrição da atividade
  - colaborador: pessoa identificada
  - data_anotacao: data/hora atual
  - status: "Aguardando prazo" — **ou "Em andamento" se Samuel já definiu o prazo
    na própria anotação** (ver passo 1); nesse caso preencher também
    prazo_combinado com a data que ele deu, direto na criação.
  - origem: "Voz" (ou "Texto", se veio de `pendentes_texto/`)
  - urgencia_detectada: "Sim"/"Não" (conforme classificação)
  - canal_usado: "Teams"/"Outlook" (conforme confirmado por Samuel)

Estrutura da tabela (criar se ainda não existir):
```sql
CREATE TABLE IF NOT EXISTS atividades_pd (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    colaborador TEXT NOT NULL,
    data_anotacao TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Aguardando prazo',
    prazo_combinado TEXT,
    ultima_cobranca TEXT,
    observacoes TEXT,
    origem TEXT NOT NULL DEFAULT 'Voz',
    urgencia_detectada TEXT NOT NULL DEFAULT 'Não',
    canal_usado TEXT,
    concluido_em TEXT
);
```

### 4. Envio da mensagem
- Abra o canal confirmado (normalmente Outlook, mesmo pra urgentes — ver passo 2)
  e envie ao colaborador uma mensagem — ver seção "Como enviar mensagens" abaixo
  (`enviar_outlook.py`, com `urgente=True` quando aplicável; Teams só se Samuel
  pedir explicitamente, por automação de tela).
- **Se o prazo ainda não foi definido** (status = "Aguardando prazo"): pedir o
  prazo para a atividade, pedindo resposta em formato curto (ex: "responda só com
  a data, formato DD/MM") para facilitar a leitura posterior.
- **Se Samuel já definiu o prazo** (status = "Em andamento" desde a criação):
  a mensagem é só um aviso, não uma pergunta — informar a atividade e o prazo já
  definido (ex: "Fulano, prazo pra isso é 10/08.") em vez de pedir uma data.

### 5. Quando o colaborador responder
- Checar a resposta com `outlook_email_search` (MCP, rápido — ver seção "Como
  enviar mensagens" abaixo) filtrando por remetente/assunto; para Teams, usar
  `chat_message_search`. Leia a resposta, extraia o prazo informado.
- Atualize o registro correspondente no banco: status = "Em andamento", prazo_combinado
  = data extraída.
- Se a resposta não tiver uma data clara, pergunte a Samuel como proceder antes de
  registrar algo incerto.

**5a. Quando é Samuel quem define (ou muda) o prazo de uma atividade já existente**
- Isso acontece por voz/texto (mesma captura do passo 0c/1), não pela resposta do
  colaborador. Depois de identificar o registro certo (passo 1 já cobre a busca —
  colaborador + título parecido, confirmando com Samuel se houver ambiguidade):
  atualizar prazo_combinado = data informada por Samuel, e status = "Em andamento"
  (some se já não estiver).
- Diferente do passo 2 (primeira mensagem de uma atividade nova), aqui **não** é
  preciso reconfirmar canal — usar o canal_usado já registrado no item. Avisar o
  colaborador do novo prazo pelo canal existente (mensagem informativa, mesmo
  tom do passo 4 quando Samuel já define o prazo na criação).
- Isso vale tanto para dar o primeiro prazo de algo que estava "Aguardando prazo"
  quanto para mudar um prazo_combinado que já existia (ex: adiar).

**5b. Reatribuição — quando Samuel passa uma atividade de uma pessoa pra outra**
- Também vem por voz/texto (ex: "passa a atividade das maçanetas do Vitor pro
  Bruno"). Identificar o registro certo do mesmo jeito do passo 1 (colaborador +
  título parecido; confirmar com Samuel se houver ambiguidade).
- Atualizar `colaborador` = novo nome. Manter `prazo_combinado` como está (o prazo
  é da atividade, não da pessoa) — só ajustar se Samuel também disser um prazo novo
  na mesma anotação (aplica passo 5a/1 junto).
- **Reconfirmar canal** com Samuel (passo 2) — a pessoa nova pode preferir Outlook
  ou Teams diferente da anterior. Depois enviar uma mensagem nova pra ela avisando
  da atividade (mesmo formato do passo 4).
- **Não notificar a pessoa antiga** — decisão de Samuel; o registro só muda de
  dono por baixo, sem mensagem de saída pra quem perdeu a atividade.
- Se o item já tinha `canal_usado` diferente do novo canal confirmado, atualizar
  `canal_usado` também.

**5c. Conclusão — três formas válidas de detectar (todas contam como confirmação)**
1. **Botão "Marcar concluído" no Painel** — Samuel clicando é confirmação direta
   dele; o painel pode gravar `status`/`concluido_em` sem passar por uma sessão do
   Claude Code (é a única gravação que o painel faz sozinho — ver seção do painel
   abaixo, é uma exceção justificada: não é decisão de IA, é clique do próprio
   Samuel).
2. **Samuel fala/digita** ("o Alexandre já concluiu as tampas") — mesma captura do
   passo 0c/1; localizar o registro (colaborador + título) e atualizar.
3. **O colaborador confirma na resposta** — via `#<id>: FEITO` na lista diária
   (passo 6a-bis) ou uma frase claramente inequívoca numa resposta de e-mail/Teams
   solta (ex: "já terminei", "está pronto", "concluído"). Se a frase for ambígua
   (ex: "tá quase", "acho que sim"), **não marcar** — perguntar a Samuel.

### 6. Checagem periódica
Disparada automaticamente pelo passo 0a (até 4x por dia: 08:00, 10:40, 13:20,
16:00). Não pede confirmação item a item — é uma exceção autorizada de antemão
pelo próprio Samuel, diferente do passo 2 (que sempre exige confirmação na primeira
mensagem de uma atividade nova). Duas partes, nesta ordem:

**6a. Verificação de respostas pendentes (fecha o passo 5 sem depender de Samuel avisar)**
- Consultar o banco filtrando: status = "Aguardando prazo".
- Para cada registro, checar se o colaborador respondeu: `outlook_email_search`
  (filtrando por remetente = e-mail do `colaboradores.json`, depois de
  `data_anotacao`) para canal_usado=Outlook, ou `chat_message_search` para
  canal_usado=Teams.
- Se achar uma resposta com data clara, extrair o prazo e atualizar o registro:
  status = "Em andamento", prazo_combinado = data extraída (mesma lógica do passo
  5). Se a resposta existir mas a data não for clara, **não adivinhar** — deixar o
  registro como está e listar no resumo para Samuel decidir.
- Se não tiver resposta ainda, deixar como está (sem cobrança nesse momento — isso
  é papel do 6b, só depois que o prazo combinado vencer).
- **Sem resposta há 2+ dias corridos** (comparar `data_anotacao` com hoje): não
  enviar nada automaticamente (isso não é uma cobrança de prazo vencido, é falta de
  retorno inicial) — só listar no resumo final como "sem retorno há N dias" para
  Samuel decidir se quer cutucar o colaborador. Não mudar o status nem enviar
  mensagem nesse caso.

**6a-bis. Verificação de respostas à lista diária (postergação e conclusão)**
- Consultar o banco filtrando: status IN ("Aguardando prazo", "Em andamento",
  "Cobrança enviada") — qualquer item em aberto pode ter sido respondido na lista
  diária do passo 7.
- Buscar respostas às mensagens "Lista de tarefas — ..." (`outlook_email_search`
  filtrando por assunto/remetente, ou `chat_message_search` pro Teams) mais
  recentes que o último envio da lista.
- Procurar linhas no formato `#<id>: CODIGO` (case-insensitive, aceitar pequenas
  variações de espaço/pontuação, mas **não** tentar adivinhar se fugir muito do
  formato — nesse caso listar no resumo pra Samuel checar manualmente):
  - `#<id>: OK` → não muda prazo_combinado; só confirma que segue no prazo. Pode
    opcionalmente atualizar `observacoes` com "confirmado em <data>".
  - `#<id>: ATRASA <nova data>` → atualizar prazo_combinado = nova data, status =
    "Em andamento" (sai de "Cobrança enviada" se estava lá), e registrar em
    `observacoes` algo como "prazo adiado de <antigo> para <novo> em <data>"
    (mantém histórico da postergação).
  - `#<id>: FEITO` → status = "Concluído", concluido_em = data/hora atual (uma das
    três formas válidas do passo 5c — é o colaborador confirmando, o que já conta
    como confirmação válida).
  - Cada linha só afeta o item com aquele `id`; se a mensagem tiver várias linhas
    (uma por atividade daquela pessoa), processar todas.
- Isso substitui qualquer necessidade de Microsoft Forms — funciona com as
  ferramentas de leitura que já temos hoje (`outlook_email_search` /
  `chat_message_search`), sem depender de nenhuma liberação de permissão extra.

**6b. Cobrança de prazos vencidos**
- Consultar o banco filtrando: status = "Em andamento" AND prazo_combinado < hoje.
- Para cada registro encontrado, enviar a cobrança pelo canal_usado (Outlook ou
  Teams) — ver seção "Como enviar mensagens" abaixo (Outlook via
  `enviar_outlook.py`; Teams por automação de tela). Para Outlook, usar
  `colaboradores.json` para achar o e-mail
  do colaborador; se o nome não estiver cadastrado, **não enviar** — deixar o
  registro como está e listar no resumo como "e-mail não cadastrado" para Samuel
  completar o arquivo.
- Depois de enviar, atualizar `ultima_cobranca` = data/hora atual e `status` =
  "Cobrança enviada".

Ao final das duas partes, reportar a Samuel um resumo direto na conversa: quantas
respostas novas foram encontradas e registradas (6a), quantos itens estão sem
retorno há 2+ dias (6a), quantas cobranças foram enviadas e por qual canal (6b), e
quantos itens ficaram pendentes em cada parte (e por quê — ex: e-mail não
cadastrado, resposta sem data clara).

### 7. Lista diária de tarefas por colaborador
Disparada automaticamente pelo passo 0b (1x por dia, na primeira sessão depois das
08:00). Não pede confirmação item a item — mesma exceção autorizada de antemão do
passo 6.

- Consultar o banco agrupando por colaborador, filtrando: status <> "Concluído"
  (ou seja, inclui "Aguardando prazo", "Em andamento" e "Cobrança enviada" — tudo
  que ainda está em aberto).
- Colaboradores sem nenhum item em aberto: pular, não enviar mensagem vazia.
- Para cada colaborador com itens em aberto, separar os itens por canal_usado.
  Se a pessoa tiver itens em mais de um canal, monta uma mensagem por canal (pode
  gerar 2 mensagens pra mesma pessoa nesse caso).
- **Formato da mensagem — cada item numerado pelo `id` real do banco (não uma
  posição 1/2/3, precisa ser estável pra identificar a resposta depois):**
  ```
  #<id> <título> — prazo atual: <prazo_combinado ou "sem prazo definido">
  ```
  E no fim da mensagem, pedir resposta em formato curto, uma linha por item:
  ```
  #<id>: OK               (segue no prazo combinado)
  #<id>: ATRASA <DD/MM>    (não vai dar, novo prazo é esse)
  #<id>: FEITO             (já concluiu)
  ```
- Assunto do e-mail (ou início da mensagem no Teams) precisa ser reconhecível
  depois, ex: "Lista de tarefas — <data de hoje>", pra diferenciar da resposta ao
  passo 4 (que é sobre um item só) quando for ler as respostas no passo 6a.
- Enviar pelo canal correspondente — ver seção "Como enviar mensagens" abaixo
  (Outlook via `enviar_outlook.py`; Teams por automação de tela). Para Outlook,
  usar `colaboradores.json` para achar o e-mail;
  se o nome não estiver cadastrado, **não enviar** — listar no resumo como "e-mail
  não cadastrado".
- Ao final, reportar a Samuel um resumo: para quantos colaboradores foi enviada a
  lista, por qual canal, e quantos ficaram pendentes (e por quê).

## Como enviar mensagens

### Outlook: COM/Interop local (método padrão, definitivo)

**Decisão (10/08/2026):** enviar e-mail pelo Outlook clássico via automação
COM/Interop local (`win32com.client`, pacote `pywin32`), **não** por
API/Graph nem por automação de tela. Script pronto: `enviar_outlook.py`
(raiz do projeto).

```python
from enviar_outlook import enviar
enviar("destinatario@dominio.com", "Assunto", "Corpo da mensagem")
enviar("destinatario@dominio.com", "Assunto", "Corpo da mensagem", urgente=True)
```

Ou via linha de comando: `python enviar_outlook.py destinatario assunto corpo [urgente]`.

**Urgente também vai por aqui (decisão de 10/08/2026):** como o Teams não
consegue enviar sem roubar a tela de Samuel (ver seção Teams abaixo), toda
atividade urgente é roteada por Outlook também, com `urgente=True` — isso
prefixa o assunto com "URGENTE" e marca importância alta no e-mail. O campo
`canal_usado` continua sendo "Outlook" nesses casos; urgência fica só em
`urgencia_detectada`.

Por que esse é o método certo:
- Controla o Outlook clássico já aberto e autenticado como Samuel — mesmo
  mecanismo que macros VBA do Office usam. **Não passa pelo Graph API**, então
  não esbarra no bloqueio de `Mail.Send`/admin consent (ver histórico abaixo).
- **Não simula clique nem digitação** — define `.To`, `.Subject`, `.Body` e
  chama `.Send()` diretamente no objeto COM. Não tem os bugs de campo que a
  automação de tela (computer-use) tinha (assunto vazando pro campo Cc, etc.).
- Testado e confirmado enviando de verdade (atividade #4, Alexandre) em
  10/08/2026 — apareceu corretamente em Itens Enviados.
- **Só funciona com o Outlook clássico (Win32)**, não com o "Novo Outlook". Se
  Samuel migrar pro Novo Outlook (toggle no canto superior direito da janela
  do Outlook), esse método para de funcionar e precisa ser reavaliado.

Para **ler** e-mails (ex: checar se um colaborador já respondeu com o prazo —
passo 5/6a), continuar usando a ferramenta MCP `outlook_email_search` — não tem
relação com o bloqueio do Graph para enviar, e já funciona normalmente.

**Histórico (não usar mais, mantido só como contexto):** as ferramentas MCP
`outlook_send_mail`/`outlook_create_draft` (Graph API) retornam 403 FORBIDDEN
nesta organização — faltam permissões `Mail.Send`/`Mail.ReadWrite` consentidas
por admin no Entra (app `api://07c030f6-5743-41b7-ba00-0a6e85f37c17`). Mesmo
que essa permissão seja liberada um dia, **não há motivo pra voltar a usar
API** — o COM/Interop já é mais rápido, mais confiável e não depende de
nenhuma permissão externa.

### Teams: só se Samuel pedir explicitamente (não é mais o canal padrão de urgente)

**Decisão (10/08/2026):** desde que ficou confirmado que o Teams não tem
nenhuma forma de enviar mensagem sem a janela estar de fato em primeiro plano
— nem `outlook_send_mail`-equivalente via API (não existe), nem UI Automation
por acessibilidade (testado: o campo de mensagem é um editor rico que só
aceita entrada de teclado real, e teclado real exige foco de janela por design
de segurança do Windows) — Teams **deixou de ser o canal automático pra
atividades urgentes** (ver passo 2). Ele só é usado se Samuel pedir Teams
explicitamente para um colaborador específico, sabendo que isso não é
zero-toque: exige ele estar na tela no momento do envio.

Quando isso acontecer, o script `enviar_teams.py` (raiz do projeto) continua
disponível:

```python
from enviar_teams import enviar_mensagem
enviar_mensagem("texto da mensagem")
```

```python
from enviar_teams import enviar_mensagem
enviar_mensagem("texto da mensagem")
```

Não existe ferramenta de envio via API neste ambiente (só leitura, com
`chat_message_search`) — isso continua valendo mesmo com esse método.

Como funciona: localiza os elementos "Digite uma mensagem" (caixa) e "Enviar"
(botão) **pelo nome**, não por posição — mais robusto que clique em
coordenada. Passo crítico descoberto no teste: a janela do Teams precisa estar
de fato em **primeiro plano do Windows** (não só ter "foco" dentro da árvore
UIA) pra digitação cair no lugar certo — por isso o script chama
`win32gui.SetForegroundWindow` antes de interagir (Samuel autorizou esse uso
em 10/08/2026, depois que o classificador de segurança bloqueou a primeira
tentativa por padrão). Testado com sucesso: texto digitado e apagado
corretamente numa conversa real, sem enviar.

**Limitação conhecida:** `enviar_mensagem()` só digita e envia na conversa que
**já está aberta e visível** na janela do Teams — não abre nem busca o
colaborador certo sozinho ainda. Antes de chamar, confirmar com screenshot
(computer-use) qual conversa está na tela; se não for a certa, abrir a
conversa certa primeiro (clicar no nome na lista lateral, se já existir, ou
`Ctrl+N` + busca pra uma conversa nova — ainda não testado de ponta a ponta,
próximo passo quando surgir um envio real por Teams).

Se `enviar_mensagem()` falhar por qualquer motivo (janela não encontrada,
elemento não encontrado), cair para automação de tela (computer-use) como
plano B: `request_access` antes de qualquer ação, screenshot pra confirmar
antes de clicar, nunca clicar às cegas.

## Mapeamento colaborador → e-mail (`colaboradores.json`)

Arquivo na raiz do projeto usado pelos passos 4, 6b e 7 para resolver o e-mail de
envio automático via Outlook. Formato: chave = nome do colaborador exatamente como
usado nas anotações de voz, valor = e-mail. Samuel precisa manter esse arquivo
atualizado; sem uma entrada para o nome, o envio automático por Outlook daquele
colaborador é pulado (fica pendente, nunca enviado para o destino errado por
adivinhação).

## Tarefa agendada do Windows (checagem periódica)

- Nome da tarefa: `PD_Checagem_4x_Dia`, criada via Agendador de Tarefas do Windows.
- Ação: abre o app Claude (`explorer.exe shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude`)
  4x por dia, em horário comercial: 08:00, 10:40, 13:20, 16:00.
- Ela **não** executa a checagem sozinha — só traz a janela do app para frente. Quem
  efetivamente roda a checagem é o passo 0a, na primeira sessão aberta depois de
  cada um desses horários (pode ser antes, durante ou depois do horário exato).
  Isso evita depender de autenticação separada de um processo invisível em segundo
  plano, que não é viável neste ambiente (o CLI standalone do app não compartilha
  login com o app principal).

## Painel de Gestão à Vista (`dashboard.py`)

Servidor web local (Flask, só acessível em `127.0.0.1:8765`, nunca exposto na
rede) que serve três funções:

1. **Quadro visual** — kanban por status (Aguardando prazo / Em andamento /
   Cobrança enviada / Concluído), lido direto do `atividades_pd.db` a cada
   carregamento de página (sempre atual, sem cache).
2. **Captura por voz** — botão "Gravar atividade" na tela chama as mesmas funções
   de `gravar_atividade.py` (em thread de fundo), salvando o `.wav` em
   `pendentes/`. Substitui o antigo atalho solto que só gravava.
3. **Captura por texto** — caixa de texto na tela; o que for digitado e enviado
   vira um arquivo em `pendentes_texto/`.
4. **Filtro por colaborador** — clicar no nome de alguém abre `/colaborador/<nome>`
   com o histórico completo daquela pessoa: total, concluídos, em atraso, em
   aberto, e uma tabela com tempo de execução calculado (`concluido_em` menos
   `data_anotacao`, ou dias em aberto se ainda não concluído).
5. **Botão "Marcar concluído"** em cada card do quadro (e na tabela do filtro por
   colaborador) — `POST /api/concluir/<id>` grava `status = "Concluído"` e
   `concluido_em` = agora, direto no banco.

**Importante: o painel quase não decide nada.** Gravação e caixa de texto só
capturam e enfileiram — a classificação de urgência, confirmação de canal,
registro e envio continuam exclusivamente numa sessão do Claude Code (passos
1–7). A **única exceção é o botão "Marcar concluído"**: como é Samuel clicando
diretamente, é confirmação explícita dele mesmo (ver passo 5c) — não precisa de
uma sessão do Claude Code mediando, por isso o próprio Flask grava direto.

**Como abre sozinho:**
- Atalho na pasta de Inicialização do Windows (`shell:startup`) roda
  `pythonw.exe dashboard.py` a cada logon — essa é a "gestão à vista" ficando de
  pé assim que o Windows liga.
- A tarefa `AtLogOn` do Agendador de Tarefas foi tentada primeiro, mas o Windows
  negou por política do domínio (`Acesso negado` ao registrar); a pasta de
  Inicialização não tem essa restrição e é o mecanismo padrão do Windows pra isso.
- O atalho "Painel P&D" na área de trabalho aponta pro mesmo `dashboard.py` — se
  já tiver um servidor rodando (checa a porta 8765 antes de subir outro), só abre
  o navegador nele; nunca duplica processo.

**Concluído deve gravar `concluido_em`:** quando Samuel confirmar que um item pode
ser marcado "Concluído" (regra geral abaixo), atualizar também
`concluido_em` = data/hora atual no mesmo UPDATE — é o que alimenta o "tempo de
execução" no filtro por colaborador. Sem isso o cálculo fica em branco.

## Acesso remoto (registrar anotação fora do computador)

Para permitir anotar por voz de qualquer lugar (não só sentado no computador), usar o
**Remote Control** do Claude Code, que conecta o app Claude no celular a uma sessão
rodando na máquina local — a execução e o acesso a arquivos continuam acontecendo no
computador, só o controle é feito pelo celular.

### Como configurar (uma vez)
1. No computador, dentro da pasta deste projeto, rodar: `claude remote-control`
   (ou, se já estiver numa sessão aberta, digitar `/remote-control`).
2. Um QR code aparece no terminal.
3. No celular, abrir o app Claude → aba "Code" → escanear o QR code.
4. A sessão fica sincronizada: dá pra falar a anotação por voz direto pelo app.

### Observações importantes
- O computador precisa estar ligado e com a sessão ativa — o Remote Control não roda
  sozinho na nuvem, ele transmite o controle de uma sessão que já está rodando
  localmente.
- Isso é compatível com a checagem periódica e a lista diária (itens 6 e 7), que
  também dependem da máquina ligada nos horários definidos.
- Para uso no dia a dia sentado à mesa, não é necessário Remote Control — basta abrir
  uma sessão do Claude Code normalmente na pasta do projeto.

## Regras gerais
- Nunca enviar mensagem sem confirmação de canal na primeira vez que uma atividade é
  criada (passo 2).
- Nunca marcar um item como "Concluído" sem uma confirmação explícita do colaborador
  ou de Samuel — ver passo 5c pras três formas válidas (botão do painel, Samuel
  falando/digitando, ou resposta clara do colaborador).
- Em caso de dúvida sobre identificar o colaborador certo (nome ambíguo, mais de uma
  pessoa com nome parecido), perguntar a Samuel antes de agir.
- Manter linguagem cordial e objetiva nas mensagens automáticas — elas são enviadas
  como se fossem do próprio Samuel.

## Configuração pendente (preencher antes do primeiro uso)
- [x] Caminho local do arquivo `atividades_pd.db` — criado nesta pasta do projeto
- [x] Definidos 4 horários de checagem periódica: 08:00, 10:40, 13:20, 16:00
      (tarefa `PD_Checagem_4x_Dia`)
- [x] Instaladas dependências do botão de gravação (`sounddevice`, `soundfile`,
      `numpy`) e do painel (`flask`)
- [x] Ajustado `PROJECT_DIR` em `gravar_atividade.py`
- [x] Preenchido `colaboradores.json` com os 7 colaboradores (apelido + nome
      completo → e-mail). Adicionar novas pessoas aqui conforme surgirem.
- [x] Remote Control testado e validado pelo app do celular
- [x] Transcrição de áudio local instalada (`transcrever.py`, usa faster-whisper,
      100% offline) — sem isso a automação por voz não funcionava de verdade
- [x] Envio de Outlook definido via COM/Interop local (`enviar_outlook.py`,
      `pywin32`) — testado enviando de verdade, não depende de nenhuma
      permissão de API/admin consent (ver seção "Como enviar mensagens")
- [x] Envio de Teams definido via UI Automation por acessibilidade
      (`enviar_teams.py`, `pywinauto` + `win32gui.SetForegroundWindow`,
      autorizado por Samuel) — testado digitando/apagando numa conversa real;
      falta testar abrir a conversa certa automaticamente (hoje precisa já
      estar aberta na tela)
- [x] Decidido (10/08/2026): urgente também roteia por Outlook (com
      `urgente=True` — assunto "URGENTE" + importância alta), não mais por
      Teams — confirmado que Teams não tem forma nenhuma de enviar sem roubar
      a tela de Samuel (nem API, nem acessibilidade). Teams vira exceção só se
      Samuel pedir explicitamente.
- [ ] Samuel pode incluir `ChatMessage.Send`/`Chat.ReadWrite` no mesmo pedido de
      liberação que já está fazendo à TI para o `Mail.Send` (mesma política de
      governança, mesmo app `07c030f6-5743-41b7-ba00-0a6e85f37c17`) — se sair,
      Teams passa a poder ser zero-toque de verdade via Graph API, sem
      precisar de janela em primeiro plano
- [x] Criado `dashboard.py` (Painel de Gestão à Vista) — quadro + botão de
      gravação + caixa de anotação por texto + filtro por colaborador, testado
      via `pythonw.exe dashboard.py` (servidor sobe, navegador abre, segunda
      execução só reabre o navegador sem duplicar servidor)
- [x] Atalho na pasta de Inicialização do Windows aponta pro painel (abre sozinho
      no logon); atalho "Painel P&D" na área de trabalho reaponta pro mesmo lugar
      (substitui o antigo atalho que só gravava áudio)
- [x] Coluna `concluido_em` adicionada em `atividades_pd.db` (migração
      `ALTER TABLE`), usada pelo filtro por colaborador para calcular tempo de
      execução
- [x] Pasta `pendentes_texto/` criada para as anotações digitadas no painel
