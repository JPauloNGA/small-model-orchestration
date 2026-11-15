# Todos os números

Consolidação de todas as medições dos dois repositórios de origem. Cada número é rastreável ao CSV correspondente.

## `llm-hardware-envelope`

### Mistral 7B Q4_K_M — GPU vs CPU

| Instrumento | Backend | Prefill (t/s) | Decode (t/s) |
|---|---|---|---|
| `llama-cli` (prompt ~19 tokens) | RX 580 Vulkan | 68,9 | 20,1 |
| `llama-cli` (prompt ~19 tokens) | Xeon CPU pura | 25,8 | 9,0 |
| `llama-bench` (pp512) | RX 580 Vulkan | 115,1 ± 0,1 | 20,6 ± 0,1 |
| `llama-bench` (pp512) | Xeon CPU pura | 91,1 ± 0,2 | 9,7 ± 0,3 |

Fonte: `evidence/medicoes.csv` + saída do `llama-bench`.

### Qwen3-30B-A3B (MoE) — três configurações

| Configuração | pp512 | tg128 | Status |
|---|---|---|---|
| GPU ingênua (`-ngl 99`) | — | — | OOM de VRAM |
| Híbrida (`-ngl 99 --n-cpu-moe 40`) | 66,90 ± 4,51 | 6,56 ± 0,14 | Rodou |
| CPU pura (`-ngl 0`) | 58,63 ± 6,23 | 8,16 ± 0,20 | Rodou |

Fonte: `evidence/medicoes_moe.csv`.

### Curva de offload

| `--n-cpu-moe` | pp512 | tg128 | Status |
|---|---|---|---|
| 20 | — | — | OOM |
| 30 | — | — | OOM |
| 40 | 65,94 ± 5,13 | 7,36 ± 0,20 | OK |
| 48 | 62,23 ± 5,18 | 6,85 ± 0,17 | OK |

Fonte: `evidence/medicoes_curva_moe.csv`.

### Prefix caching

| Modelo | TTFT frio | TTFT quente | Ganho |
|---|---|---|---|
| Mistral 7B | 8.415 ms | 847 ms | 9,9× |
| Qwen3-30B-A3B | 67.960 ms | 911 ms | 74,6× |

Fonte: `evidence/medicoes_prefix.csv` e `evidence/medicoes_prefix_moe.csv`.

### Pipeline de voz

| Etapa | Modelo | Latência |
|---|---|---|
| STT | Whisper tiny | 207 ms (extrapolado para 3 s de áudio) |
| LLM | Qwen 0.5B | 604 ms (40 tokens a 66,26 tok/s) |
| TTS | Piper | 81 ms (mediana de 3 frases) |
| **Total** | | **892 ms** |

Fonte: `evidence/medicoes_voz.csv`.

### Assistente funcional (`assistant.py`)

| Entrada | STT | LLM | TTS | Total |
|---|---|---|---|---|
| `jfk.wav` (11 s) | 482 ms | 2.663 ms | 844 ms | 3.989 ms |

O tempo do LLM inclui o cold start do `llama-server`. Com o servidor quente, a latência esperada é a da tabela acima (~892 ms).

Fonte: saída do `assistant.py` em `evidence/medicoes_voz.csv` (nota).

### Diário de texto (5 perguntas)

| Pergunta | Resposta | Latência | Acertou? |
|---|---|---|---|
| Capital da Austrália | Canberra | 2.264 ms (cold start) | Sim |
| 3 maçãs − 1 | two apples | 133 ms | Sim |
| Por que o céu é azul | scattering of sunlight | 315 ms | Sim |
| Fato interessante | Burj Khalifa, 828 m | 679 ms | Sim |
| Reverter string em Python | `s[::-1]` | 266 ms | Sim |

Fonte: `notes/diario.md`.

## `llm_study`

### Experimento 1 — PT-BR vs EN

| Métrica | PT-BR | EN | Diferença |
|---|---|---|---|
| Tokens do prompt | 43 | 40 | −7% no inglês |
| Tokens gerados | 50 | 36 | −28% no inglês |
| Tempo total | 1,26 s | 0,91 s | −28% no inglês |
| Velocidade | 39,60 t/s | 39,55 t/s | Igual |

Fonte: `data/idioma.csv`.

### Experimento 2 — Comparação de modelos

| Modelo | Parâmetros | Velocidade PT-BR (t/s) | Velocidade EN (t/s) |
|---|---|---|---|
| Qwen 2.5 1.5B | 1.5B | 39,64 | 40,47 |
| Qwen 2.5 3B | 3B | 29,02 | 29,17 |
| Llama 3.2 1B | 1B | 22,11 | 22,45 |

Fonte: `data/modelos.csv`.

### Experimento 3 — KV caching

| Cenário | Tokens prompt | Tokens gerados | Tempo | Velocidade |
|---|---|---|---|---|
| Pergunta 1 (contexto longo) | 203 | 28 | 0,70 s | 40,16 t/s |
| Pergunta 2 (mesmo contexto, cache) | 253 | 13 | 0,32 s | 40,01 t/s |
| Pergunta isolada (sem cache) | 47 | 23 | 0,58 s | 39,36 t/s |

Fonte: `data/kv_caching.csv`.

### Experimento 4 — Quantização (Q4 vs Q8)

| Quantização | Tamanho | Tempo | Velocidade |
|---|---|---|---|
| Q4_K_M | ~986 MB | 1,26 s | 39,79 t/s |
| Q8_0 | ~1,6 GB | 1,37 s | 36,37 t/s |

Fonte: `data/quantizacao.csv`.

### Experimento 5 — CPU vs GPU (Vulkan)

| Configuração | Velocidade |
|---|---|
| CPU (PyTorch) | ~7 t/s |
| GPU (Vulkan) | ~40 t/s |

Ganho: ~6×.

### Experimento 8 — Roteador

| Pergunta | Categoria | Especialista | Classificação | Total | Velocidade |
|---|---|---|---|---|---|
| Inverter lista em Python | código | qwen2.5-coder:7b | 2,94 s | 12,22 s | 14,73 t/s |
| Servo motor vs motor de passo | mecatrônica | jarvis | 2,33 s | 7,41 s | 38,92 t/s |
| Sensor de efeito Hall | mecatrônica | jarvis | 2,36 s | 7,20 s | 38,52 t/s |
| Quem foi Alan Turing? | geral | qwen2.5:3b | 2,28 s | 23,64 s | 28,66 t/s |
| Descreva a imagem | visão | llava:7b | 14,06 s | 41,68 s | 22,98 t/s |

Fonte: `data/roteador.csv`.

### Experimento 9 — Especialista vs generalista

| Modelo | Tempo | Tokens | Velocidade | Qualidade |
|---|---|---|---|---|
| Especialista (Coder 7B) | 19,70 s | 255 | 15,08 t/s | Código idiomático, docstring, generator |
| Generalista (Qwen 7B) | 17,49 s | 300 | 20,42 t/s | Funcional, list comprehension, sem docstring |

### Experimento 10 — RAG

| Pergunta | Sem RAG | Com RAG (busca) | Com RAG (geração) | Com RAG (total) |
|---|---|---|---|---|
| Microcontrolador vs microprocessador | 6,15 s | 2,12 s | 4,36 s | 6,48 s |
| O que é servo motor? | 6,13 s | 2,14 s | 4,78 s | 6,92 s |

### Experimento 11 — Comparação estendida

| Modelo | Parâmetros | Velocidade | VRAM | Tokens PT-BR | Tokens EN |
|---|---|---|---|---|---|
| Qwen 2.5 1.5B | 1.5B | ~39 t/s | ~1,0 GB | 43 | 40 |
| Llama 3.2 1B | 1B | ~22,5 t/s | 1,41 GB | 39 | 36 |
| Gemma 2 2B | 2B | ~28,4 t/s | 1,80 GB | 23 | 20 |
| Qwen 2.5 3B | 3B | ~29,2 t/s | 2,01 GB | 43 | 40 |

### Experimento 12 — Quantização (Q4 vs Q8, com VRAM)

| Quantização | Velocidade | VRAM | Tempo |
|---|---|---|---|
| Q4_K_M | 38,79 t/s | 1,09 GB | 1,29 s |
| Q8_0 | 36,74 t/s | 1,70 GB | 1,36 s |

## Nota sobre comparabilidade

Os números do `llm-hardware-envelope` vêm do `llama.cpp` direto. Os do `llm_study` vêm do Ollama (que usa `llama.cpp` como backend, mas com overhead de gerenciamento). Isso significa que a velocidade absoluta não é diretamente comparável entre os dois repositórios — mas as conclusões qualitativas (GPU > CPU, Q4 > Q8, cache reduz latência) se sustentam em ambos.