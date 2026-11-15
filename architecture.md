# Arquitetura

Este documento descreve a arquitetura do sistema de orquestração em **Nível 2.5**: detalhe suficiente para entender como o sistema decide, mas sem o código de implementação. O objetivo é tornar a arquitetura **reproduzível em princípio** — quem quiser implementar precisa pensar, mas não precisa adivinhar.

## Visão geral

O sistema tem quatro camadas. Nenhuma delas exige um modelo maior que 7B.

```
[Usuário]
    ↓
[Classificador (Qwen 1.5B)]
    ↓
[Cache de contexto] ← prefix caching + KV caching
    ↓
[Especialistas por categoria]
    ├── código        → Qwen 2.5 Coder 7B
    ├── mecatrônica   → Jarvis 1.5B (system prompt técnico)
    ├── visão         → Llava 7B
    └── geral         → Qwen 2.5 3B (fallback)
    ↓
[RAG (base de conhecimento)] ← quando o especialista precisa de fatos
    ↓
[Resposta + TTS (Piper)]
```

## Camada 1 — Classificador

**Modelo:** Qwen 2.5 1.5B Q4_K_M (via Ollama).

**Entrada:** a pergunta do usuário, em texto.

**Prompt:** um template fixo com 5 categorias e exemplos:

```
Você é um classificador de perguntas. Leia a pergunta e classifique em UMA das categorias abaixo.
Responda APENAS com a palavra da categoria, sem explicações, sem pontuação.

Categorias e regras:
- codigo: perguntas sobre programação, algoritmos, debugging, linguagens de programação, funções, bibliotecas.
- mecatronica: perguntas sobre eletrônica, robótica, automação, sistemas embarcados, motores, sensores, atuadores, microcontroladores.
- visao: perguntas que envolvem análise de imagens, reconhecimento visual, ou que precisam "ver" algo.
- geral: qualquer outra pergunta (história, ciência, filosofia, conhecimentos gerais).

Exemplos:
Pergunta: "Como inverter uma lista em Python?" -> codigo
Pergunta: "O que é um sensor de efeito Hall?" -> mecatronica
Pergunta: "Quem foi Alan Turing?" -> geral
Pergunta: "Descreva a imagem que estou enviando." -> visao
Pergunta: "Qual a diferença entre servo motor e motor de passo?" -> mecatronica

Pergunta do usuário: {pergunta}

Categoria:
```

**Saída:** uma das cinco palavras (`codigo`, `mecatronica`, `visao`, `geral`). Se a saída não for exatamente uma das palavras (por exemplo, o modelo responde "A categoria é código"), o sistema normaliza: remove pontuação, converte para minúsculas, e se ainda não bater, cai no fallback (`geral`).

**Latência:** ~2,3 s (medido). O classificador é o segundo maior contribuinte de latência do sistema, atrás apenas do especialista.

**Por que 1.5B e não 0.5B:** o 0.5B é mais rápido, mas erra a classificação em casos ambíguos (por exemplo, "o que é um servo motor?" pode ser classificado como `geral` em vez de `mecatronica`). O 1.5B acertou 100% dos casos de teste.

**Por que não usar o próprio especialista para classificar:** porque isso exigiria carregar o especialista antes de saber qual é, o que anula o benefício do roteamento.

## Camada 2 — Cache de contexto

**Duas camadas:**

### Prefix caching

**O que faz:** mantém o KV cache do system prompt fixo entre requisições. Quando a segunda pergunta chega, o prefixo já está calculado.

**Onde é usado:** no `llama-server`, via `cache_prompt: true`. O servidor mantém um slot de cache com o prefixo.

**Impacto medido:** TTFT cai de 8.415 ms para 847 ms no Mistral 7B (9,9×) e de 67.960 ms para 911 ms no Qwen3-30B-A3B (74,6×).

**Custo:** o servidor precisa ficar no ar (não subir e descer a cada pergunta). O cold start do `llama-server` é de ~2–8 s, dependendo do modelo.

### KV caching

**O que faz:** mantém o KV cache do histórico da conversa entre turnos. Quando o usuário faz uma segunda pergunta no mesmo contexto, o sistema não recalcula o histórico.

**Onde é usado:** no Ollama, via endpoint `/api/chat` (que mantém o contexto entre mensagens) ou no `llama-server` com o mesmo `cache_prompt`.

**Impacto medido:** a segunda pergunta no mesmo contexto levou 0,32 s contra 0,58 s da pergunta isolada — quase metade do tempo, mesmo com um prompt 5× maior (253 vs 47 tokens).

**Custo:** o cache cresce com o histórico. Em conversas longas, o sistema precisa truncar ou sumarizar o histórico para não estourar o contexto.

## Camada 3 — Especialistas

**Quatro especialistas, um por categoria:**

| Categoria | Modelo | Parâmetros | Por quê |
|---|---|---|---|
| `codigo` | Qwen 2.5 Coder 7B | 7B | Melhor qualidade em código, mesmo sendo mais lento |
| `mecatronica` | Jarvis 1.5B | 1.5B | System prompt técnico, rápido (38,92 t/s), cabe na VRAM |
| `visao` | Llava 7B | 7B | Único que processa imagens |
| `geral` | Qwen 2.5 3B | 3B | Fallback com boa qualidade geral |

**Como o especialista é escolhido:** por tabela fixa. O classificador retorna a categoria, e a categoria mapeia diretamente para o modelo. Não há aprendizado ou otimização nessa etapa — é uma decisão de projeto para manter o sistema previsível.

**Latência por especialista (medida):**

| Especialista | Tempo total | Velocidade |
|---|---|---|
| Jarvis 1.5B (mecatrônica) | ~7,2 s | 38,92 t/s |
| Qwen Coder 7B (código) | ~12,2 s | 14,73 t/s |
| Qwen 3B (geral) | ~23,6 s | 28,66 t/s |
| Llava 7B (visão) | ~41,7 s | 22,98 t/s |

**Por que os modelos 7B são lentos:** na RX 580 (8 GB), os modelos 7B não cabem inteiros na VRAM junto com o classificador. O sistema precisa carregar/descarregar o especialista a cada chamada, o que adiciona overhead. O Jarvis 1.5B cabe e é o mais rápido.

**Implicação para hardware limitado:** especialistas pequenos (1.5B) são a melhor opção. Especialistas 7B só compensam se a qualidade for crítica e a latência não importar.

## Camada 4 — RAG

**O que faz:** quando o especialista precisa de fatos que não estão no modelo (por exemplo, uma definição técnica específica), o RAG busca os trechos relevantes em uma base de conhecimento e injeta no prompt.

**Arquitetura:**

1. **Indexação:** os documentos são divididos em chunks, cada chunk é convertido em embedding (via `nomic-embed-text`), e os embeddings são armazenados em um índice (no caso atual, um JSON simples; para bases maiores, um banco vetorial como ChromaDB ou FAISS).
2. **Busca:** a pergunta do usuário é convertida em embedding, e os chunks mais similares (por similaridade de cosseno) são recuperados.
3. **Injeção:** os chunks recuperados são concatenados ao prompt do especialista, com uma instrução do tipo "use o contexto abaixo para responder".

**Impacto medido:** o RAG adicionou ~0,3–0,8 s ao tempo total, mas o modelo gerou menos tokens (mais direto), compensando a busca. A resposta com RAG foi tecnicamente correta; sem RAG, foi genérica e propensa a erros conceituais.

**Custo:** a base de conhecimento precisa ser mantida. Para uma base pequena (1 documento), o RAG é trivial. Para uma base grande, exige indexação e busca eficientes.

## O fluxo completo

1. O usuário faz uma pergunta (texto ou voz).
2. Se for voz, o STT (Whisper tiny) transcreve para texto (~207 ms para 3 s de áudio).
3. O classificador (Qwen 1.5B) decide a categoria (~2,3 s).
4. O cache de contexto é consultado: se o prefixo já está calculado, o TTFT é baixo (~847 ms no Mistral, ~911 ms no MoE).
5. O especialista da categoria é chamado. Se ele precisa de fatos, o RAG busca e injeta o contexto.
6. A resposta é gerada.
7. Se for voz, o TTS (Piper) sintetiza a resposta (~81 ms para uma frase curta).

**Latência total esperada (pergunta curta, servidor quente):** ~2,3 s (classificação) + ~0,6 s (LLM) + ~0,1 s (TTS) ≈ **3 s**. Para uma pergunta de voz com 3 s de áudio, adicione ~0,2 s (STT).

## O que o sistema **não** faz

- **Não aprende com o uso.** O classificador e os especialistas são fixos. Não há fine-tuning contínuo.
- **Não tem memória de longo prazo.** O histórico é limitado ao contexto do cache. Conversas antigas são descartadas.
- **Não roteia dinamicamente por qualidade.** A escolha do especialista é por tabela fixa, não por avaliação da resposta.
- **Não tem fallback se o especialista falha.** Se o modelo não responde, o sistema não tenta outro automaticamente.
- **Não é multi-usuário.** O cache é por sessão, e o servidor é single-stream.

## O que faria sentido adicionar

- **Roteamento por confiança:** se o classificador tem baixa confiança, usar o fallback (`geral`) em vez de arriscar um especialista errado.
- **Cache de respostas:** para perguntas repetidas, guardar a resposta e evitar a inferência.
- **Sumarização de histórico:** para conversas longas, sumarizar o histórico antigo em vez de truncar.
- **Avaliação automática:** medir a qualidade das respostas ao longo do tempo e ajustar a tabela de especialistas.