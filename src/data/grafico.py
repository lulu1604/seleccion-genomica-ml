import os
import matplotlib.pyplot as plt

# Datos del estudio de Abdollahi-Arpanahi
modelos = ['GB', 'BayesB', 'GBLUP', 'RF', 'CNN', 'MLP']
correlaciones = [0.36, 0.34, 0.33, 0.32, 0.29, 0.26]

# Crear la figura
fig, ax = plt.subplots(figsize=(8, 5))
barras = ax.barh(modelos, correlaciones, color='lightgray')

# Destacar la barra de GBLUP (línea base) en color tomate
barras[2].set_color('tomato')

# Mostrar los valores numéricos sobre cada barra
for barra in barras:
    ancho = barra.get_width()
    ax.text(ancho + 0.005, barra.get_y() + barra.get_height()/2, 
            f'{ancho}', va='center', fontsize=11, fontweight='bold')

# Configuración visual para la presentación
ax.set_xlabel('Correlación (Rendimiento de predicción)', fontsize=11)
ax.set_title('Comparativa de Modelos Predictivos (Estudio Abdollahi-Arpanahi)', fontweight='bold', fontsize=12)
ax.invert_yaxis()  # Mantiene el modelo con mejor rendimiento arriba (GB)
plt.tight_layout()

# Guardar la imagen en alta resolución
os.makedirs('results', exist_ok=True)
plt.savefig('results/abdollahi-barras.png', dpi=300)