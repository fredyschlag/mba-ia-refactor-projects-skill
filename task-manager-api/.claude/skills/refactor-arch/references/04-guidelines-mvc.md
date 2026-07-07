# Guidelines de Arquitetura MVC Alvo (Fase 3)

O objetivo da Fase 3 não é só "criar pastas" — é fazer cada pedaço de código morar no lugar cuja responsabilidade ele de fato cumpre. Use estas regras para decidir onde cada trecho vai, e para justificar decisões quando o encaixe não for óbvio.

## Estrutura de diretórios alvo

Adapte os nomes de arquivo à convenção da linguagem, mas a forma é a mesma em qualquer stack:

```
src/                      # (ou raiz do projeto, se a stack não usar pasta src/)
├── config/               # configuração centralizada, lida de variáveis de ambiente
│   └── settings.<ext>
├── models/                # 1 arquivo por entidade/domínio, nunca um models.<ext> único com tudo
│   ├── <entidade_a>.<ext>
│   └── <entidade_b>.<ext>
├── routes/  (ou views/)    # definição de endpoints — fina, delega tudo ao controller
│   └── <dominio>_routes.<ext>
├── controllers/           # orquestra o fluxo de uma requisição
│   └── <dominio>_controller.<ext>
├── middlewares/            # cross-cutting: tratamento de erro centralizado, auth, logging
│   └── error_handler.<ext>
└── app.<ext>                # composition root: monta tudo, não tem lógica de negócio
```

Se o projeto já tiver algumas dessas pastas (caso comum em projetos "parcialmente organizados"), não recrie do zero — mova/corrija o que estiver no lugar errado e preserve o que já está certo.

## Responsabilidade de cada camada

### Models
- Dona dos dados e das regras de negócio **intrínsecas à entidade** (validação de invariantes, cálculos que dependem só dos próprios campos, ex: `is_overdue()`, `calcular_total()`).
- Acesso a dados (queries, ORM) mora aqui — nunca em uma rota ou controller.
- **Não conhece HTTP**: nada de `request`, `response`, `jsonify`, status code, dentro de um Model.
- Um arquivo por entidade/domínio. Se um "God File" de models cobre produtos + usuários + pedidos, ele vira `models/produto.py`, `models/usuario.py`, `models/pedido.py`.

### Views / Routes
- Só define endpoints e o mapeamento HTTP → função do controller (verbo + path + handler).
- Faz o parsing básico da requisição (ex: pegar `request.json`) e repassa ao controller — não valida regra de negócio, não decide status code de erro de domínio, não acessa o banco.
- Deve ser curta o suficiente para ler inteira e entender todos os endpoints de relance.

### Controllers
- Orquestra o fluxo: recebe o que a rota já parseou, chama Model(s)/Service(s) na ordem certa, decide o que responder (sucesso/erro, status code, formato do payload).
- Não deve conter SQL cru nem regra de negócio complexa — se uma regra é reaproveitável ou depende só dos dados de uma entidade, ela pertence ao Model, não ao Controller.
- Pode combinar múltiplos Models/Services numa única operação (isso é orquestração, não regra de negócio de entidade — cabe aqui).

### Config
- Único lugar que lê variáveis de ambiente (`os.environ`/`process.env`) e monta a configuração da aplicação (chave secreta, string de conexão, credenciais de serviços externos).
- **Nenhum segredo literal no código** — valores sensíveis vêm de env vars; documente as variáveis esperadas (ex: em um `.env.example`) sem preencher valores reais.

### Middlewares
- Tratamento de erro **centralizado**: um único handler que captura exceções não tratadas e devolve uma resposta padronizada, em vez de `try/except`/`try/catch` repetido em cada rota.
- Outras preocupações transversais (autenticação, logging de requisições, CORS) também moram aqui, não espalhadas pelos controllers.

### Composition root (`app.py`/`app.js`/equivalente)
- Instancia o framework, registra config, registra rotas/blueprints/routers, registra middlewares, e sobe o servidor. Não deve conter lógica de negócio nem definição de endpoint inline — se um `@app.route` aparece direto no arquivo principal, ele deveria estar em `routes/`.

## Direção de dependência

`routes` → `controllers` → `models`. Nunca o inverso (um Model não deve importar um Controller ou conhecer o framework HTTP). Isso é o que torna o Model testável isoladamente, sem subir servidor — o mesmo teste que a Fase 2 usa para diagnosticar "God Class" é o critério para validar a Fase 3.

## O que "refatorar para MVC" NÃO significa aqui

Não é só mover código de lugar preservando os bugs. O objetivo do desafio é reestruturar **e** eliminar os anti-patterns encontrados na Fase 2 no mesmo processo — ao mover uma query para dentro do Model, já a parametrize (mata SQL Injection); ao mover config para `config/`, já remova o segredo hardcoded; ao consolidar validação duplicada, já unifique numa função só. Use o `05-playbook-refatoracao.md` para os padrões de transformação de cada tipo de apontamento.
