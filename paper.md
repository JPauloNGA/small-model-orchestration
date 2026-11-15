# Small Model Orchestration: Capacidade de Agente sem Modelos Gigantes

**Autor:** JPauloNGA
**Data:** Novembro de 2026
**Repositórios:** [`llm-hardware-envelope`](https://github.com/JPauloNGA/llm-hardware-envelope), [`llm_study`](https://github.com/JPauloNGA/llm_study)

## Abstract

Este trabalho investiga se um agente de IA local e útil pode emergir da orquestração de modelos pequenos, em vez do escalonamento de um modelo monolítico. Em hardware de 2016 (Xeon E5-2680 v4 + RX 580 8 GB), medimos o envelope de inferência de modelos densos e MoE, o impacto do prefix caching, e a viabilidade de um sistema de roteamento com especialistas e RAG. Os resultados mostram que (1) a GPU só compensa quando o modelo cabe inteiro na VRAM; (2) o prefix caching reduz o TTFT em 9,9× no denso e 74,6× no MoE; (3) um pipeline de voz completo cabe em 892 ms; e (4) um roteador de 1,5B classifica corretamente 100% das categorias e direciona para especialistas que respondem em 7–24 s. Concluímos que a orquestração eficiente de modelos pequenos é uma alternativa viável a modelos monolíticos gigantes em hardware limitado.

## 1. Introdução

A engenharia de IA contemporânea persegue o escalonamento monolítico: mais parâmetros, mais tokens de contexto, mais VRAM. Esse caminho tem um custo que raramente é explicitado: um modelo de 70B em Q4 ocupa ~40 GB, o que exige hardware que a maioria dos desenvolvedores não tem. A questão que este trabalho coloca é: **é possível ter capacidade de agente útil sem um modelo gigante?**

A hipótese é que a inteligência útil emerge da **composição** — roteamento, cache, ferramentas externas —, não do tamanho bruto do modelo. Essa hipótese não é nova: a literatura recente sobre agentes mostra que frameworks com ferramentas e raciocínio passo a passo melhoram substancialmente modelos pequenos. O que este trabalho acrescenta é uma **medição empírica** em hardware obsoleto, com números reproduzíveis.

## 2. Metodologia

### 2.1 Hardware

Xeon E5-2680 v4 (14c/28t, Broadwell), 32 GB DDR4 quad-channel 2133 MHz, AMD RX 580 2048SP (8 GB, Vulkan), Windows 10.

### 2.2 Software

`llama.cpp` build b12384 (commit 3549c274d), compilado com `-DGGML_VULKAN=ON`. Ollama para os experimentos do `llm_study`. Python 3.13 para análise.

### 2.3 Modelos

Mistral 7B Q4_K_M (denso), Qwen3-30B-A3B Q4_K_M (MoE), Qwen 0.5B/1.5B/3B, Llama 3.2 1B, Gemma 2 2B, Whisper tiny, Piper.

### 2.4 Protocolo

Todas as medições usam prompts fixos, `temperature=0`, e 3 repetições quando possível. A mediana é o valor reportado. Os CSVs brutos estão nos repositórios de origem.

## 3. Resultados

### 3.1 O envelope de hardware

O Mistral 7B cabe inteiro na VRAM (4 GB em 7,3 GB livres). A GPU entrega 20,6 tok/s de decode contra 9,7 tok/s da CPU — uma vantagem de 2,2×. O prefill saturado (512 tokens) mostra uma vantagem menor: 115,1 vs 91,1 tok/s (1,3×).

O Qwen3-30B-A3B não cabe (17,28 GB). A configuração ingênua (`-ngl 99`) falha por OOM. A configuração híbrida (`--n-cpu-moe 40`) roda a 7,36 tok/s; a CPU pura roda a 8,16 tok/s. **A CPU pura vence o híbrido** porque evita o tráfego de experts pela PCIe 3.0.

### 3.2 O cache como alavanca

O prefix caching reduz o TTFT de 8.415 ms para 847 ms no Mistral (9,9×) e de 67.960 ms para 911 ms no MoE (74,6×). O TTFT quente é praticamente o mesmo nos dois modelos (911 vs 847 ms), o que mostra que o cache elimina o custo de reprocessar o prefixo **independentemente do tamanho do modelo**.

### 3.3 O pipeline de voz

STT (207 ms) + LLM (604 ms) + TTS (81 ms) = 892 ms. O pipeline cabe em menos de 1 segundo no Xeon, sem GPU, com modelos que somam menos de 1 GB em disco.

### 3.4 A orquestração

O roteador classifica 100% das categorias corretamente. O especialista de mecatrônica (Jarvis 1.5B) responde em ~7 s a 38,92 tok/s. Os modelos 7B (Coder, Llava) são mais lentos porque precisam ser carregados/descarregados a cada chamada.

O RAG adiciona ~0,3–0,8 s ao tempo total, mas o modelo gera menos tokens (mais direto), compensando a busca. A resposta com RAG é tecnicamente correta; sem RAG, é genérica e propensa a erros conceituais.

## 4. Discussão

### 4.1 O que os números implicam

Para hardware limitado, a arquitetura certa não é "o maior modelo que cabe", mas "o conjunto de modelos que se complementam". Um classificador de 1,5B + especialistas de 1,5B–7B + RAG entrega mais capacidade útil que um único modelo de 7B sem orquestração.

### 4.2 O que os números não implicam

Os resultados não sustentam a tese de que modelos pequenos são **equivalentes** a modelos grandes em todas as tarefas. Eles sustentam que, **para um agente local com ferramentas e cache**, a diferença é menor do que o tamanho sugere. Tarefas que exigem raciocínio multi-etapas ou conhecimento enciclopédico amplo continuam favorecendo modelos maiores.

### 4.3 A conexão com a literatura

A ideia de especialização não é nova: modelos de mistura de especialistas (MoE) e adaptadores de baixo posto (LoRA) já exploram a composição em vez do escalonamento. O que este trabalho propõe é a versão factível em hardware de 2016: roteamento de modelos inteiros por categoria, com RAG como memória externa. A diferença é de escala e de método, não de princípio.

## 5. Limitações

- **Single-stream:** as medições não cobrem concorrência.
- **Uma máquina:** outro hardware pode dar resultados diferentes.
- **Uma execução por configuração (na maioria):** as medições do MoE e do Mistral foram repetidas 3 vezes; as do `llm_study` foram execuções únicas.
- **Backends diferentes:** o `llm-hardware-envelope` usou `llama.cpp`; o `llm_study` usou Ollama.
- **O roteador não foi testado em produção:** os 5 casos de teste são uma amostra pequena.

## 6. Conclusão

Um agente local útil não precisa de um modelo gigante. Precisa de um sistema que roteia, cacheia e complementa modelos pequenos com ferramentas externas. Em hardware de 2016, essa arquitetura entrega um pipeline de voz em 892 ms, um roteador que classifica corretamente 100% das categorias, e um MoE de 30B que roda a 8,16 tok/s em CPU pura. A inteligência útil emerge da composição, não do tamanho.

## Referências

- `llm-hardware-envelope`: https://github.com/JPauloNGA/llm-hardware-envelope
- `llm_study`: https://github.com/JPauloNGA/llm_study