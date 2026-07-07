# Template do Relatório de Auditoria (Fase 2)

Use **exatamente** esta estrutura para o relatório da Fase 2 — é o formato definido no enunciado do desafio, e existe para que os apontamentos sejam fáceis de escanear visualmente e para que o relatório salvo em `reports/audit-project-N.md` tenha o mesmo formato em qualquer projeto auditado, independente da stack. Os rótulos estruturais (`Project`, `Stack`, `Files`, `Summary`, `Findings`, `File`, `Description`, `Impact`, `Recommendation`, `Total`, e a pergunta final) ficam em inglês exatamente como abaixo — é o texto literal esperado. O **conteúdo** de cada apontamento (a descrição, o impacto, a recomendação em si) é escrito em português, como no exemplo do próprio enunciado.

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório do projeto>
Stack:   <linguagem + framework>
Files:   <N> analyzed | ~<LOC> lines of code

Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

Findings

[<SEVERITY>] <Nome curto do anti-pattern>
File: <caminho/relativo/arquivo.ext>:<linha ou intervalo de linhas>
Description: <o que foi encontrado, citando o trecho relevante quando ajudar>
Impact: <por que isso importa — consequência concreta, não genérica>
Recommendation: <o que fazer para corrigir, referenciando o padrão do playbook quando aplicável>

[<SEVERITY>] <próximo apontamento...>
...

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Regras de preenchimento

- **Ordene os apontamentos por severidade**: todos os CRITICAL primeiro, depois HIGH, depois MEDIUM, depois LOW. Dentro da mesma severidade, ordem de descoberta é suficiente.
- **O campo `File:` deve ter caminho e linha exatos** — abra o arquivo e confirme o número da linha antes de escrever; não estime. Se o apontamento abrange um intervalo (ex: um arquivo inteiro sem separação de camadas), cite o intervalo real (`app.py:1-89`), não apenas o nome do arquivo.
- **O campo `Description:`** deve ser específico o suficiente para alguém que nunca viu o código entender o problema sem abrir o arquivo — cite o trecho de código problemático quando isso ajudar.
- **O campo `Impact:`** deve conectar o apontamento a uma consequência real (segurança, corretude, manutenção, performance) — evite frases genéricas como "isso é uma má prática".
- **O campo `Recommendation:`** deve ser acionável — aponte para o padrão de transformação correspondente em `05-playbook-refatoracao.md` quando existir um.
- **Não invente apontamentos**: cada linha do relatório deve corresponder a algo real, verificável no código. É melhor reportar 6 apontamentos sólidos do que 12 onde metade é forçada.
- **Contagem de linhas de código (`~LOC`)** pode ser aproximada (`wc -l` nos arquivos-fonte relevantes, ignorando dependências).

## Depois de imprimir o relatório

Pare e pergunte explicitamente ao usuário se deseja prosseguir para a Fase 3, usando exatamente a frase do template acima (`Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`). **Não comece a modificar nenhum arquivo antes de receber uma resposta afirmativa explícita do usuário nesta conversa** — uma permissão de ferramenta concedida pelo usuário não substitui essa confirmação; é uma pergunta de revisão humana do relatório, não uma autorização técnica de execução de comando.
