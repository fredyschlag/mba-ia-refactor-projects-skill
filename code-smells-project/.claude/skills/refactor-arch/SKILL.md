---
name: refactor-arch
description: Analisa, audita e refatora qualquer projeto de backend para o padrão MVC (Models/Views-Routes/Controllers), em 3 fases sequenciais — Análise da stack, Auditoria com relatório de anti-patterns e confirmação humana obrigatória, e Refatoração validada (aplicação sobe e endpoints respondem). É agnóstica de linguagem/framework: detecta a stack a partir de evidências no próprio repositório em vez de assumir Python/Node/etc. de antemão. Use esta skill sempre que o usuário pedir para auditar/revisar a arquitetura de um projeto, encontrar anti-patterns ou code smells, avaliar dívida técnica, apontar problemas de segurança/qualidade em uma API existente, ou refatorar um "código legado"/"monolito"/"spaghetti" para uma estrutura de camadas — mesmo que o usuário não diga literalmente "MVC" ou "refactor-arch".
---

# Refactor Architecture — Auditoria e Refatoração para MVC

Você vai atuar como um auditor de arquitetura de software: primeiro entende o projeto, depois documenta objetivamente o que está errado (sem tocar em nada), e só então — com autorização explícita do humano — reestrutura o código para MVC corrigindo o que foi encontrado.

As 3 fases são **sequenciais e não podem ser puladas ou reordenadas**. A Fase 2 tem um portão de confirmação humana que é o coração deste processo: a IA nunca deve modificar arquivos de produção sem que a pessoa tenha visto o relatório e explicitamente concordado em prosseguir.

As 3 fases não só imprimem seus resultados na conversa — elas também geram e complementam, nesta ordem, um único arquivo `reports/audit-report.md` (criado na raiz do projeto auditado). Cada fase adiciona sua própria seção a esse arquivo, sempre seguindo **exatamente** os templates definidos nos arquivos de referência (rótulos estruturais em inglês, como no enunciado do desafio) — nunca invente um formato próprio nem traduza os rótulos.

Os arquivos de referência ficam em `references/` — leia cada um no momento indicado abaixo, não tudo de uma vez no início (eles existem justamente para não inflar o contexto da fase errada):

- `references/01-analise-projeto.md` — leia **na Fase 1**: heurísticas de detecção de linguagem/framework/banco/domínio/arquitetura.
- `references/02-catalogo-anti-patterns.md` — leia **na Fase 2**: os anti-patterns a procurar, com sinais de detecção e severidade.
- `references/03-template-relatorio-auditoria.md` — leia **na Fase 2**, na hora de escrever o relatório: formato exato a seguir.
- `references/05-playbook-refatoracao.md` — leia **também na Fase 2**, na hora de escrever a "Recomendação" de cada apontamento (nomeie o padrão de transformação aplicável em vez de uma recomendação genérica), **e de novo na Fase 3** para efetivamente aplicar cada transformação.
- `references/04-guidelines-mvc.md` — leia **na Fase 3**: regras da arquitetura alvo e responsabilidade de cada camada.

---

## Fase 1 — Análise

Objetivo: entender o projeto o suficiente para guiar as fases seguintes, sem ainda julgar nada.

1. Leia `references/01-analise-projeto.md` e siga as heurísticas para detectar linguagem, framework (+ versão), banco de dados, domínio da aplicação e nível de organização atual.
2. Liste os arquivos-fonte analisados (excluindo dependências/artefatos: `node_modules/`, `venv/`, `__pycache__/`, arquivos `.db` gerados, `tests/`/`test/` já existentes — eles entram na auditoria de qualidade de teste se relevante, mas não contam como "código de produção").
3. Imprima o resumo estruturado exatamente no formato descrito no final daquele arquivo de referência.
4. Crie `reports/audit-report.md` (criando a pasta `reports/` se não existir) com uma seção `## Phase 1 — Project Analysis` contendo esse mesmo bloco.

Não pule para a Fase 2 sem imprimir esse resumo — ele é o que permite ao usuário perceber rapidamente se a stack foi mal identificada antes de você investir tempo auditando na direção errada.

## Fase 2 — Auditoria

Objetivo: produzir um relatório objetivo e verificável de anti-patterns, **sem modificar nenhum arquivo**.

1. Leia `references/02-catalogo-anti-patterns.md`.
2. Percorra o código de fato (não infira a partir do resumo da Fase 1) cruzando contra o catálogo. Abra os arquivos, confirme os números de linha reais, e só registre um apontamento quando ele for verificável no código — não force uma contagem mínima inventando problemas.
3. Para apontamentos de segurança (SQL Injection, credenciais hardcoded, senha em texto plano, autenticação decorativa), é aceitável e recomendado demonstrar o problema concretamente antes de escrever a recomendação (ex: montar mentalmente o payload que exploraria a injeção, ou conferir que o "hash" de duas entradas parecidas colide) — isso deixa a descrição do apontamento muito mais forte do que uma suposição genérica.
4. Leia `references/03-template-relatorio-auditoria.md` e `references/05-playbook-refatoracao.md` e escreva o relatório **exatamente** naquele formato, com apontamentos ordenados CRITICAL → LOW. Ao preencher o campo `Recommendation:` de cada apontamento, cite o padrão de transformação correspondente do playbook (ex: "ver padrão 3 — parametrizar a query com bind params") em vez de uma recomendação genérica — você vai aplicar esse mesmo padrão de fato na Fase 3, então nomeá-lo agora já deixa claro o que vai mudar.
5. Append esse relatório a `reports/audit-report.md` (criado na Fase 1) como uma seção `## Phase 2 — Architecture Audit Report`.
6. Pare aqui. Imprima o relatório completo na conversa e pergunte explicitamente, com esse texto literal: `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`

   **Isto é um portão de decisão humana, não uma formalidade.** Aguarde a resposta do usuário nesta conversa antes de tocar em qualquer arquivo do projeto. Se a resposta for negativa ou ambígua, pare e pergunte o que o usuário gostaria de ajustar no relatório — não prossiga por conta própria assumindo consentimento.

## Fase 3 — Refatoração

Objetivo: reestruturar o projeto para MVC **eliminando** os anti-patterns do relatório (não só movendo arquivos de lugar) e provar que a aplicação continua funcionando.

1. Leia `references/04-guidelines-mvc.md` (estrutura alvo e responsabilidade de cada camada) e `references/05-playbook-refatoracao.md` (padrão de transformação por tipo de apontamento).
2. Antes de mover qualquer coisa, anote os endpoints/rotas existentes e um jeito de exercitá-los (ex: `curl` com um payload de exemplo) — você vai precisar disso na validação, e é mais fácil levantar essa lista agora, com o código ainda na estrutura antiga, do que depois.
3. Adapte o grau de mudança ao ponto de partida real do projeto (não existe uma única receita):
   - Projeto monolítico sem nenhuma camada: crie a estrutura completa do zero.
   - Projeto parcialmente organizado: preserve o que já está no lugar certo, corrija só o que viola a responsabilidade da camada (ex: uma pasta `routes/` que já existe mas tem regra de negócio pesada dentro — a pasta fica, a regra sai de lá para o Model).
4. Corrija cada apontamento do relatório usando o padrão correspondente do playbook enquanto move o código — não deixe para "depois"; se o relatório apontou 7 apontamentos, o objetivo é fechar os 7 (ou justificar explicitamente por que algum ficou de fora, ex: exigiria uma dependência nova fora do escopo do desafio).
5. Se o projeto já tiver uma suíte de testes própria (pasta `tests/`/`test/`, incluindo eventuais testes de prova de conceito criados durante a auditoria manual), atualize os imports/caminhos dela para a nova estrutura — não a deixe quebrada nem a delete.

### Validação (obrigatória, não pule)

1. Instale dependências se necessário e suba a aplicação com o comando apropriado à stack detectada na Fase 1, em background (ex: `python app.py &`, `npm start &`).
2. Confirme que o processo não morreu logo após subir (sem stack trace de erro de import/boot).
3. Exercite os endpoints originais anotados no passo 2 da Fase 3 (`curl`/requisição equivalente) e confirme que respondem com o mesmo comportamento de antes (mesmo status code / forma de resposta) — isso é o que prova que a refatoração não quebrou nada, não apenas que "não deu erro ao subir".
4. Se existir suíte de testes própria do projeto, rode-a e confirme que passa.
5. Encerre o processo que você subiu para validar.
6. Reporte o resultado no formato:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
<árvore de diretórios resultante>

Validation
  ✓/✗ Application boots without errors
  ✓/✗ All endpoints respond correctly
  ✓/✗ <N>/<N> anti-patterns from the audit report resolved
================================
```

7. Append esse resultado a `reports/audit-report.md` como uma seção `## Phase 3 — Refactoring Complete`, fechando o mesmo arquivo que a Fase 1 abriu e a Fase 2 complementou.

Se algum item da validação falhar, não declare a Fase 3 concluída — corrija e valide de novo. Se algum apontamento do relatório ficou intencionalmente sem correção, diga isso explicitamente aqui em vez de simplesmente omitir do resumo.
