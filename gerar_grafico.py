import matplotlib.pyplot as plt

# Dados consolidados dos dois repositórios
categorias = ["MoE CPU", "MoE híbrido", "Mistral GPU", "Mistral CPU", "Qwen 1.5B"]
valores = [8.16, 7.36, 20.6, 9.7, 39.64]
cores = ["#e74c3c", "#e67e22", "#3498db", "#2980b9", "#2ecc71"]

fig, ax = plt.subplots(figsize=(10, 5))
barras = ax.bar(categorias, valores, color=cores)
ax.set_ylabel("tokens/s (decode)")
ax.set_title("Velocidade de decode por configuração (hardware: Xeon 2016 + RX 580)")
ax.bar_label(barras, fmt="%.2f")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("results/consolidacao.png", dpi=150)
print("Grafico salvo em results/consolidacao.png")