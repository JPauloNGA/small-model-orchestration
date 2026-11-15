# Reprodutibilidade

Este documento descreve como repetir as medições que sustentam a tese. Ele não contém os scripts de implementação (roteador, RAG, benchmarks), mas contém o **método**: versões, modelos, comandos e a correspondência entre cada comando e cada CSV.

## Hardware de referência

| Componente | Especificação |
|---|---|
| CPU | Intel Xeon E5-2680 v4 (14c/28t, Broadwell, sem AVX-512) |
| RAM | 32 GB DDR4 quad-channel 2133 MHz |
| GPU | AMD Radeon RX 580 2048SP, 8 GB (Vulkan) |
| Disco | SSD SATA |
| SO | Windows 10 (build 19045) |

## Software

| Ferramenta | Versão | Onde foi usada |
|---|---|---|
| `llama.cpp` | build b12384 (commit 3549c274d) | `llm-hardware-envelope` |
| Vulkan SDK | 1.4.363.1 | build do `llama.cpp` com `-DGGML_VULKAN=ON` |
| Ollama | versão do `llm_study` (out/2026) | `llm_study` |
| Python | 3.13 (Miniconda) | scripts de análise e gráficos |
| `faster-whisper` | 1.2.1 | pipeline de voz |
| `piper-tts` | 1.8.0 | TTS do pipeline de voz |

## Modelos

| Modelo | Quantização | Tamanho | Onde foi usado |
|---|---|---|---|
| Mistral-7B-Instruct-v0.2 | Q4_K_M | 4,07 GB | `llm-hardware-envelope` (GPU vs CPU, prefix caching) |
| Qwen3-30B-A3B | Q4_K_M | 17,28 GB | `llm-hardware-envelope` (MoE, curva de offload, prefix caching) |
| Qwen2.5-0.5B-Instruct | Q4_K_M | 463 MiB | pipeline de voz e diário de texto |
| Whisper tiny.en | f16 | 77 MB | STT do pipeline de voz |
| Piper en_US-lessac-medium | — | 63 MB | TTS do pipeline de voz |
| Qwen2.5 1.5B / 3B, Llama 3.2 1B, Gemma 2 2B | Q4_K_M | variados | `llm_study` (comparação de modelos) |

## Comandos por experimento

### Mistral 7B — GPU vs CPU (`llm-hardware-envelope`)

```powershell
# GPU
.\llama-bench.exe -m C:\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf -ngl 100 -t 28 -p 512 -n 128 -r 3

# CPU
.\llama-bench.exe -m C:\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf -ngl 0 -t 28 -p 512 -n 128 -r 3
```

CSV correspondente: `evidence/medicoes.csv` (llama-cli) e os valores de `llama-bench` no README.

### MoE Qwen3-30B-A3B — três configurações (`llm-hardware-envelope`)

```powershell
# GPU ingênua (falha por OOM)
.\llama-bench.exe -m C:\models\Qwen3-30B-A3B-Q4_K_M.gguf -ngl 99 -t 28 -p 512 -n 128 -r 3

# Híbrida (N=40)
.\llama-bench.exe -m C:\models\Qwen3-30B-A3B-Q4_K_M.gguf -ngl 99 --n-cpu-moe 40 -t 28 -p 512 -n 128 -r 3

# CPU pura
.\llama-bench.exe -m C:\models\Qwen3-30B-A3B-Q4_K_M.gguf -ngl 0 -t 28 -p 512 -n 128 -r 3
```

CSV: `evidence/medicoes_moe.csv`.

### Curva de offload (`llm-hardware-envelope`)

```powershell
foreach ($n in 20,30,40,48) {
    .\llama-bench.exe -m C:\models\Qwen3-30B-A3B-Q4_K_M.gguf -ngl 99 --n-cpu-moe $n -t 28 -p 512 -n 128 -r 3
}
```

CSV: `evidence/medicoes_curva_moe.csv`.

### Prefix caching (`llm-hardware-envelope`)

```powershell
# Servidor
.\llama-server.exe -m C:\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf -ngl 0 -t 28 -c 2048 -np 1 --port 8080

# Requisição com cache_prompt: false (frio) e true (quente)
# O corpo JSON está descrito em notes/metodologia.md
```

CSV: `evidence/medicoes_prefix.csv` (Mistral) e `evidence/medicoes_prefix_moe.csv` (MoE).

### Pipeline de voz (`llm-hardware-envelope`)

```powershell
# Whisper
.\whisper-cli.exe -m C:\models\voice\ggml-tiny.en.bin -f C:\models\voice\jfk.wav -t 28

# LLM
.\llama-bench.exe -m C:\models\voice\qwen2.5-0.5b-instruct-q4_k_m.gguf -ngl 0 -t 28 -p 128 -n 64 -r 3

# TTS
python scripts\bench_tts.py
```

CSV: `evidence/medicoes_voz.csv`.

### Experimentos do `llm_study`

Os comandos estão documentados no README do [`llm_study`](https://github.com/JPauloNGA/llm_study), na seção "Como Executar". Os CSVs consolidados estão em `data/` deste repositório.

## O que não é reproduzível sem os scripts

Os scripts de implementação do roteador (`router.py`), do RAG (`rag_index.py`, `rag_query.py`) e dos benchmarks do `llm_study` **não estão públicos**. O que está público é o método: as categorias do roteador, o formato do prompt do classificador, a arquitetura do RAG (embeddings + similaridade de cosseno + injeção de contexto). Quem quiser replicar precisa implementar esses componentes — o que é factível, mas exige trabalho.

## Limitações

- **Single-stream:** as medições não cobrem concorrência nem throughput agregado.
- **Uma máquina:** todos os números vêm do mesmo hardware. Outro hardware pode dar resultados diferentes.
- **Uma execução por configuração (na maioria):** as medições do MoE e do Mistral foram repetidas 3 vezes; as do `llm_study` foram execuções únicas.
- **O `llm_study` usou Ollama; o `llm-hardware-envelope` usou `llama.cpp` direto.** Os números não são diretamente comparáveis entre os dois repositórios (backend diferente), mas as conclusões qualitativas se sustentam.