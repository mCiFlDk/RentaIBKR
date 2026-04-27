<div align="center">

# DEGIRO IRPF Analyzer

### Informes fiscales accionables para Renta WEB a partir de los CSV de DEGIRO

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-2457ff?style=for-the-badge&logo=gnu&logoColor=white)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Markdown report](https://img.shields.io/badge/Output-Markdown-111111?style=for-the-badge&logo=markdown&logoColor=white)](#11-salidas-generadas)
[![Excel report](https://img.shields.io/badge/Output-Excel-217346?style=for-the-badge&logo=microsoft-excel&logoColor=white)](#11-salidas-generadas)

[![GitHub Sponsors](https://img.shields.io/badge/Support-GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/flaviogrillo1)
[![Buy Me a Coffee](https://img.shields.io/badge/Donate-Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/flaviogrillo)
[![Stripe](https://img.shields.io/badge/Donate-Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)

</div>

> Convierte `Transactions.csv` y `Account.csv` en un informe que te dice qué meter en Hacienda, qué líneas llevan check de recompra y qué cifras deben cuadrar con Renta WEB.

## Apoya el proyecto

Si este proyecto te ahorra tiempo, errores o revisión manual en tu declaración, puedes apoyar su mantenimiento aquí:

<p align="center">
  <a href="https://buymeacoffee.com/flaviogrillo">
    <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me a Coffee" style="height: 56px; width: 236px;" />
  </a>
</p>

<p align="center">
  <a href="https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00">
    <img src="https://img.shields.io/badge/Support%20with%20Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white" alt="Support with Stripe" />
  </a>
</p>

- **[GitHub Sponsors](https://github.com/sponsors/flaviogrillo1)**
- **[Buy Me a Coffee](https://buymeacoffee.com/flaviogrillo)**
- **[Stripe](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)**

Cada aportación ayuda a mantener el cálculo fiscal, las validaciones de FIFO y la compatibilidad con futuros cambios del extracto de DEGIRO.

El script lee `Transactions.csv` y `Account.csv`, calcula FIFO por ISIN, aplica la regla española de recompra de valores homogéneos, separa líneas fiscales F2 para Renta WEB, detecta pérdidas no computables por la regla de los 2 meses y genera:

- un informe Markdown (`.md`);
- un Excel opcional (`.xlsx`) con pestañas operativas para Hacienda;
- controles de cuadre con las casillas de Renta WEB.

> Este programa es una herramienta de apoyo. No sustituye a Renta WEB ni a un asesor fiscal. El contribuyente debe revisar los datos antes de presentar la declaración.

Licencia: `GPL-3.0`. Si redistribuyes o modificas este proyecto, debes respetar los términos de [LICENSE](LICENSE).

---

## Índice

1. [Qué problema resuelve](#1-qué-problema-resuelve)
2. [Qué calcula el script](#2-qué-calcula-el-script)
3. [Marco fiscal que implementa](#3-marco-fiscal-que-implementa)
4. [Requisitos](#4-requisitos)
5. [Archivos de entrada](#5-archivos-de-entrada)
6. [Instalación](#6-instalación)
7. [Uso rápido](#7-uso-rápido)
8. [Argumentos disponibles](#8-argumentos-disponibles)
9. [Cómo elegir `--history-end-date`](#9-cómo-elegir---history-end-date)
10. [Cómo elegir `--fx-mode`](#10-cómo-elegir---fx-mode)
11. [Salidas generadas](#11-salidas-generadas)
12. [Cómo leer el informe Markdown](#12-cómo-leer-el-informe-markdown)
13. [Cómo usar el Excel](#13-cómo-usar-el-excel)
14. [Cómo trasladar los datos a Renta WEB](#14-cómo-trasladar-los-datos-a-renta-web)
15. [Regla de los 2 meses: cómo la aplica el script](#15-regla-de-los-2-meses-cómo-la-aplica-el-script)
16. [Ventas parcialmente bloqueadas: el punto más importante](#16-ventas-parcialmente-bloqueadas-el-punto-más-importante)
17. [Dividendos, retenciones y doble imposición](#17-dividendos-retenciones-y-doble-imposición)
18. [Compensaciones en la base del ahorro](#18-compensaciones-en-la-base-del-ahorro)
19. [Limitaciones conocidas](#19-limitaciones-conocidas)
20. [Errores frecuentes](#20-errores-frecuentes)
21. [Checklist antes de presentar](#21-checklist-antes-de-presentar)
22. [Ejemplos de uso](#22-ejemplos-de-uso)
23. [Estructura interna del cálculo](#23-estructura-interna-del-cálculo)
24. [Validaciones que realiza](#24-validaciones-que-realiza)
25. [Tests recomendados](#25-tests-recomendados)
26. [Referencias legales y fuentes](#26-referencias-legales-y-fuentes)

---

## 1. Qué problema resuelve

DEGIRO no calcula necesariamente el resultado fiscal español. En particular, puede no reflejar correctamente:

- FIFO global del contribuyente;
- regla de recompra de valores homogéneos;
- pérdidas no computables por recompra;
- pérdidas diferidas que se liberan más adelante;
- separación de líneas en Renta WEB cuando una venta está parcialmente afectada;
- AutoFX, costes de transacción y liquidación en EUR;
- dividendos y retenciones en divisa;
- compensaciones entre saldos de la base del ahorro.

Este script genera una salida más útil para declarar acciones en Renta WEB.

El objetivo no es solo calcular un resultado neto. El objetivo es decir:

```text
qué líneas meter en Hacienda,
qué importes poner,
qué líneas llevan check de recompra,
qué pérdidas son computables,
qué pérdidas están diferidas,
y qué alertas revisar antes de presentar.
```

---

## 2. Qué calcula el script

El script calcula:

- compras y ventas por ISIN;
- valor de adquisición FIFO;
- valor de transmisión neto;
- resultado real de cada transmisión;
- pérdida no computable por recompra de valores homogéneos;
- pérdida diferida integrada desde ventas anteriores;
- resultado fiscal integrable;
- líneas F2 listas para Renta WEB;
- suma de ganancias integrables;
- suma de pérdidas integrables;
- resultado neto F2;
- dividendos, intereses y retenciones detectadas;
- compensación de base del ahorro;
- advertencias críticas.

También genera un Excel con pestañas específicas:

```text
01 Resumen
02 Renta WEB
03 Checks 2M
04 Control Renta WEB
05 Diferidas
06 Compensaciones
07 Capital mobiliario
08 Insights
09 Alertas
10 Resumen final
```

---

## 3. Marco fiscal que implementa

### 3.1 FIFO

Para valores homogéneos, el script considera transmitidos primero los valores adquiridos primero.

En la práctica:

```text
si compras 100 acciones en enero y 100 en marzo,
y vendes 80 en abril,
el coste FIFO corresponde a las 80 primeras acciones de enero.
```

---

### 3.2 Valores homogéneos

El script usa el ISIN como clave principal de homogeneidad.

Para acciones ordinarias de una misma sociedad, normalmente esto es suficiente. Aun así, hay casos que requieren revisión manual:

- acciones con distinta titularidad;
- acciones privativas vs gananciales;
- ADR frente a acción ordinaria;
- distintas clases de acciones;
- cambios de ISIN;
- fusiones o spin-offs;
- eventos corporativos.

---

### 3.3 Regla de recompra de valores homogéneos

Si vendes con pérdida y compras valores homogéneos dentro del plazo legal, la pérdida puede no ser computable en ese momento.

Para acciones admitidas a negociación, el script aplica por defecto:

```text
2 meses antes o después de la venta
```

Para valores no admitidos a negociación, la Ley contempla un plazo de 1 año. El script permite configurar ventanas por ISIN mediante:

```python
REPLACEMENT_WINDOW_MONTHS_BY_ISIN: dict[str, int] = {}
```

Por defecto:

```python
DEFAULT_REPLACEMENT_WINDOW_MONTHS = 2
```

---

### 3.4 Pérdidas diferidas

Una pérdida bloqueada no desaparece.

El script la modela así:

1. Venta con pérdida.
2. Se detectan valores homogéneos comprados dentro de la ventana legal.
3. La pérdida no computable se añade al coste fiscal del lote de sustitución.
4. Cuando ese lote se vende, la pérdida diferida se integra.

---

### 3.5 Check de Renta WEB

Cuando una pérdida no es computable por recompra, en Renta WEB no basta con meter transmisión y adquisición.

Esa línea debe marcarse como pérdida no computable por recompra de valores homogéneos.

El script lo muestra en:

```text
02 Renta WEB
03 Checks 2M
04 Control Renta WEB
```

---

## 4. Requisitos

- Python 3.11 o superior recomendado.
- Sin dependencias externas obligatorias.
- Conexión a internet la primera vez que necesite descargar tipos de cambio ECB/BCE.
- CSV exportados de DEGIRO:
  - `Transactions.csv`
  - `Account.csv`

El script usa solo librerías estándar:

```text
argparse
csv
json
zipfile
dataclasses
datetime
decimal
pathlib
urllib
xml
```

No requiere `pandas`, `openpyxl` ni `xlsxwriter`.

---

## 5. Archivos de entrada

### 5.1 `Transactions.csv`

Archivo de operaciones de DEGIRO.

El script espera el formato CSV exportado por DEGIRO y utiliza, entre otros, estos campos por posición:

| Campo usado | Contenido esperado |
|---|---|
| Fecha | Fecha de operación |
| Hora | Hora de operación |
| Producto | Nombre del activo |
| ISIN | Código ISIN |
| Número | Cantidad comprada o vendida |
| Precio | Precio unitario |
| Divisa | Divisa de cotización |
| Valor local | Importe bruto en divisa local |
| Valor EUR | Importe bruto convertido a EUR |
| Costes EUR | Costes de transacción |
| Total EUR | Total liquidado |
| ID orden | Identificador de orden |

El script adapta una variante de 17 columnas de DEGIRO insertando una columna vacía antes del identificador de orden.

---

### 5.2 `Account.csv`

Archivo de movimientos de cuenta de DEGIRO.

Se usa para:

- dividendos;
- retenciones;
- intereses;
- gastos del broker;
- eventos corporativos;
- movimientos en divisa.

El script convierte importes no EUR a EUR usando el tipo ECB/BCE de la fecha valor.

---

## 6. Instalación

Guarda el script como:

```bash
degiro_irpf.py
```

Comprueba la versión de Python:

```bash
python --version
```

Ejecuta desde la carpeta donde estén los CSV:

```bash
ls
```

Debe verse algo parecido a:

```text
degiro_irpf.py
Transactions.csv
Account.csv
```

---

## 7. Uso rápido

Uso recomendado para IRPF 2025:

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --fx-mode degiro --history-end-date 2026-02-28
```

Si indicas `--output` pero no `--excel-output`, el script genera automáticamente un Excel con el mismo nombre base:

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28
```

Generará:

```text
informe_irpf_2025.md
informe_irpf_2025.xlsx
```

---

## 8. Argumentos disponibles

### `--transactions`

Ruta al CSV de operaciones de DEGIRO.

Obligatorio.

Ejemplo:

```bash
--transactions Transactions.csv
```

---

### `--account`

Ruta al CSV de movimientos de cuenta de DEGIRO.

Obligatorio.

Ejemplo:

```bash
--account Account.csv
```

---

### `--year`

Ejercicio fiscal que quieres analizar.

Obligatorio.

Ejemplo:

```bash
--year 2025
```

---

### `--output`

Ruta del informe Markdown.

Opcional.

Ejemplo:

```bash
--output informe_irpf_2025.md
```

Si no se indica, el informe se imprime por consola.

---

### `--excel-output`

Ruta del Excel de salida.

Opcional.

Ejemplo:

```bash
--excel-output informe_irpf_2025.xlsx
```

Si no se indica pero sí se indica `--output`, el script genera automáticamente un `.xlsx` con el mismo nombre base que el `.md`.

---

### `--fx-mode`

Criterio de conversión para operaciones no EUR.

Valores disponibles:

```text
degiro
ecb
favorable
```

Recomendado:

```bash
--fx-mode degiro
```

Ver explicación detallada en [Cómo elegir `--fx-mode`](#10-cómo-elegir---fx-mode).

---

### `--history-end-date`

Fecha final cubierta por el histórico exportado.

Formato:

```text
YYYY-MM-DD
```

Ejemplo:

```bash
--history-end-date 2026-02-28
```

Este argumento es fundamental para validar recompras posteriores dentro de la ventana de 2 meses.

Debe ser la fecha real hasta la que cubren los CSV, no una fecha inventada.

---

### `--carry-gains-losses`

Pérdidas patrimoniales de ejercicios anteriores pendientes de compensar.

Ejemplo:

```bash
--carry-gains-losses 1250.45
```

Por defecto:

```text
0
```

---

### `--carry-income-losses`

Rendimientos negativos del capital mobiliario de ejercicios anteriores pendientes de compensar.

Ejemplo:

```bash
--carry-income-losses 300
```

Por defecto:

```text
0
```

---

### `--carryover-json`

Permite introducir arrastres desde un JSON.

Ejemplo:

```bash
--carryover-json carryovers.json
```

Formato:

```json
{
  "income_losses": "300",
  "gains_losses": "1250.45"
}
```

---

### `--savings-tax-rate-hint`

Tipo orientativo para estimar la deducción por doble imposición internacional.

Ejemplo:

```bash
--savings-tax-rate-hint 0.19
```

No es necesario para simples compraventas sin dividendos.

---

## 9. Cómo elegir `--history-end-date`

La regla de recompra mira compras dentro de una ventana posterior a la venta.

Por eso, si declaras 2025, no basta siempre con exportar hasta 31/12/2025. Para ventas con pérdida de noviembre o diciembre, hay que saber si recompraste en enero o febrero de 2026.

Recomendación general para IRPF 2025:

```bash
--history-end-date 2026-02-28
```

Ejemplos:

| Última venta con pérdida | Fecha mínima recomendable |
|---|---|
| 02/09/2025 | 02/11/2025 o posterior |
| 15/11/2025 | 15/01/2026 o posterior |
| 31/12/2025 | 28/02/2026 o posterior |

Si no indicas `--history-end-date`, el script usa la fecha de la última operación cargada y genera advertencia.

---

## 10. Cómo elegir `--fx-mode`

### 10.1 `degiro`

Modo recomendado para uso práctico.

Usa el importe en EUR que DEGIRO proporciona cuando existe.

Ventajas:

- coincide con el efectivo realmente liquidado;
- integra AutoFX si está reflejado en el total EUR;
- facilita cuadrar con movimientos de cuenta;
- evita separar artificialmente tipo de cambio y coste de broker.

Ejemplo:

```bash
--fx-mode degiro
```

---

### 10.2 `ecb`

Recalcula importes usando tipos de referencia del Banco Central Europeo.

Ventajas:

- criterio externo y uniforme;
- útil para comprobaciones;
- evita depender del tipo de cambio aplicado por el broker.

Inconvenientes:

- puede no coincidir con el efectivo liquidado;
- requiere especial cuidado con comisiones y AutoFX;
- puede generar diferencias frente a DEGIRO.

Ejemplo:

```bash
--fx-mode ecb
```

---

### 10.3 `favorable`

Disponible en el código, pero no recomendado para declarar.

Este modo compara una declaración completa con DEGIRO y otra con ECB y conserva la más favorable.

No es un criterio fiscal estable. Si se usa, el informe lo marcará como alerta crítica.

Recomendación:

```text
No usar --fx-mode favorable para presentar la declaración.
```

---

## 11. Salidas generadas

### 11.1 Markdown

Ejemplo:

```text
informe_irpf_2025.md
```

Contiene:

- resumen ejecutivo;
- qué meter en Renta WEB;
- líneas con check de regla 2 meses;
- control de casillas;
- validación de pérdidas diferidas;
- compensaciones;
- dividendos y retenciones;
- insights;
- alertas;
- resumen final para copiar.

---

### 11.2 Excel

Ejemplo:

```text
informe_irpf_2025.xlsx
```

Pestañas:

| Pestaña | Uso |
|---|---|
| `01 Resumen` | Visión ejecutiva |
| `02 Renta WEB` | Líneas a introducir |
| `03 Checks 2M` | Líneas que llevan check de recompra |
| `04 Control Renta WEB` | Cuadre con casillas 0339/0340 |
| `05 Diferidas` | Pérdidas generadas, integradas y pendientes |
| `06 Compensaciones` | Base del ahorro |
| `07 Capital mobiliario` | Dividendos, intereses, retenciones |
| `08 Insights` | Lectura fiscal relevante |
| `09 Alertas` | Riesgos antes de presentar |
| `10 Resumen final` | Bloque para copiar manualmente |

---

## 12. Cómo leer el informe Markdown

### 12.1 Resumen ejecutivo

La sección más importante para decidir si el informe es limpio o requiere revisión.

Campos clave:

| Campo | Interpretación |
|---|---|
| Resultado F2 integrable | Resultado que entra en ganancias/pérdidas patrimoniales antes de compensaciones |
| Pérdidas no computables 2M | Pérdidas que requieren check de recompra |
| Pendiente a 31/12 | Pérdida diferida que seguía bloqueada al cierre del ejercicio |
| Pendiente final histórico | Pérdida diferida que sigue bloqueada al final de todos los datos cargados |
| Líneas con check | Si hay que marcar pérdida no computable en Renta WEB |

---

### 12.2 Qué meter en Renta WEB

Es la tabla operativa principal.

Columnas:

| Columna | Qué significa |
|---|---|
| Activo | Producto |
| ISIN | Identificador |
| Fecha / Grupo | Fecha concreta o grupo agregado |
| Transmisión EUR | Valor de transmisión a introducir |
| Adquisición EUR | Valor de adquisición a introducir |
| Resultado real | Ganancia/pérdida real de la línea |
| Pérdida no computable 2M | Parte que no debe computar por recompra |
| ¿Marcar check recompra? | `SÍ` o `NO` |
| Resultado integrable | Resultado que debe sumar a Renta WEB |
| Acción en Renta WEB | Instrucción concreta |

---

### 12.3 Checks de regla de 2 meses

Lista solo las líneas donde hay que marcar el check.

Si aparece una línea aquí, no debe mezclarse con líneas normales.

---

### 12.4 Control casillas Renta WEB

Esta sección está pensada para cuadrar con Hacienda.

| Campo del informe | Campo de Renta WEB |
|---|---|
| Suma ganancias integrables acciones negociadas | Casilla 0339 |
| Suma pérdidas integrables acciones negociadas | Casilla 0340 |
| Resultado neto integrable F2 | 0339 - 0340 |
| Pérdidas no computables 2M | Informativo; no debe sumar a pérdidas integrables |

Si Renta WEB no cuadra, revisa:

1. líneas con check;
2. ventas parcialmente bloqueadas;
3. líneas agrupadas indebidamente;
4. errores de redondeo;
5. importes introducidos a mano.

---

## 13. Cómo usar el Excel

El Excel está pensado para trabajar más rápido que con el Markdown.

### Orden recomendado

1. Abrir `01 Resumen`.
2. Revisar si hay alertas críticas.
3. Ir a `02 Renta WEB`.
4. Copiar cada línea en Renta WEB.
5. Ir a `03 Checks 2M`.
6. Marcar el check solo en las líneas listadas.
7. Ir a `04 Control Renta WEB`.
8. Comparar con las casillas 0339 y 0340 de Hacienda.
9. Revisar `09 Alertas` antes de presentar.

---

## 14. Cómo trasladar los datos a Renta WEB

### 14.1 Acciones cotizadas / admitidas a negociación

En Renta WEB, normalmente irás a:

```text
Ganancias y pérdidas patrimoniales
→ Ganancias y pérdidas derivadas de transmisiones de acciones admitidas a negociación
```

Introduce las líneas de la pestaña:

```text
02 Renta WEB
```

Para cada línea:

| En Excel | En Renta WEB |
|---|---|
| Activo | Sociedad emisora |
| ISIN | Identificación del valor, si procede |
| Transmisión EUR | Valor de transmisión |
| Adquisición EUR | Valor de adquisición |
| Check recompra | Casilla de pérdida no computable por recompra |
| Resultado integrable | Control final |

---

### 14.2 Si una línea tiene check `SÍ`

Debe tratarse como pérdida no computable por recompra de valores homogéneos.

No la mezcles con otra línea sin check.

---

### 14.3 Si una línea tiene check `NO`

Se introduce normalmente.

Si el resultado es negativo, debe sumar a la casilla de pérdidas integrables.

---

## 15. Regla de los 2 meses: cómo la aplica el script

Para cada venta con pérdida:

1. Calcula la pérdida real:
   ```text
   transmisión - adquisición FIFO
   ```

2. Busca compras homogéneas dentro de la ventana:
   ```text
   venta - 2 meses
   venta + 2 meses
   ```

3. Determina cuántos títulos permanecen o se recompran.

4. Bloquea la pérdida proporcional.

5. Añade la pérdida bloqueada al coste fiscal del lote de sustitución.

6. Cuando se venda el lote de sustitución, la pérdida diferida se integra.

---

## 16. Ventas parcialmente bloqueadas: el punto más importante

Este es el caso que suele causar descuadres con Hacienda.

Ejemplo:

```text
Pérdida real de una venta: -1.755,25 EUR
Pérdida no computable por recompra: 1.176,01 EUR
Pérdida computable: -579,24 EUR
```

Si metes esa venta como una sola línea y marcas el check de recompra, Renta WEB puede excluir toda la pérdida, incluyendo la parte que sí era computable.

Por eso el script crea dos líneas F2:

### Línea 1: tramo no computable

```text
Check recompra: SÍ
Resultado integrable: 0
Pérdida no computable: 1.176,01 EUR
```

### Línea 2: tramo computable

```text
Check recompra: NO
Resultado integrable: -579,24 EUR
```

Esto permite que Renta WEB incluya la pérdida computable en la casilla de pérdidas y excluya solo la parte realmente bloqueada.

---

## 17. Dividendos, retenciones y doble imposición

El script detecta movimientos que contienen palabras como:

```text
dividend
dividendo
retención
withholding
interest
```

Y calcula:

- dividendos brutos;
- intereses;
- retención extranjera;
- renta extranjera asociada;
- estimación orientativa de límite si usas `--savings-tax-rate-hint`.

### Importante

La doble imposición internacional afecta normalmente a dividendos e intereses extranjeros.

No afecta a una simple compraventa de acciones sin dividendos.

---

## 18. Compensaciones en la base del ahorro

El script estima compensaciones entre:

- ganancias/pérdidas patrimoniales;
- rendimientos del capital mobiliario;
- arrastres de ejercicios anteriores.

La compensación cruzada entre bloques se limita al porcentaje legal aplicable. El script usa el 25%.

Se muestran:

- saldo F2 antes de compensaciones;
- saldo de capital mobiliario;
- compensación entre bloques;
- arrastres usados;
- saldo final estimado.

Renta WEB debe hacer el cálculo definitivo.

---

## 19. Limitaciones conocidas

El script no resuelve automáticamente:

- mismo ISIN en otros brokers;
- ventas sin histórico completo;
- posiciones cortas;
- ventas en corto;
- préstamo de valores;
- acciones no admitidas a negociación si requieren regla de 1 año;
- ETFs con tratamiento específico;
- fondos de inversión;
- traspasos de fondos;
- criptomonedas;
- opciones;
- futuros;
- warrants;
- CFDs;
- derechos de suscripción;
- dividendos en acciones;
- acciones liberadas;
- splits;
- reverse splits;
- spin-offs;
- fusiones;
- cambios de ISIN;
- ampliaciones de capital;
- operaciones corporativas complejas;
- titularidades distintas;
- operaciones en cuentas conjuntas.

---

## 20. Errores frecuentes

### 20.1 Renta WEB no cuadra con el informe

Revisa:

```text
04 Control Renta WEB
```

Si la casilla 0339 no cuadra, probablemente falta o sobra una ganancia.

Si la casilla 0340 no cuadra, revisa especialmente:

- líneas con check 2M;
- ventas parcialmente bloqueadas;
- pérdidas introducidas como no computables completas cuando solo lo eran parcialmente.

---

### 20.2 El informe muestra check 2M pero pendiente final 0

Esto puede ser correcto.

Significa:

```text
la pérdida estuvo bloqueada temporalmente,
pero se liberó después al vender los lotes de sustitución.
```

No confundas:

```text
pérdida no computable en una línea
```

con:

```text
pérdida pendiente al final del histórico
```

---

### 20.3 Sale FIFO incompleto

Significa que vendiste más títulos de los que el histórico cargado permite justificar.

Solución:

- cargar histórico anterior;
- incorporar operaciones de otros brokers;
- revisar si hubo eventos corporativos.

El script no aplica automáticamente la regla de recompra a ventas con FIFO incompleto.

---

### 20.4 Tengo el mismo ISIN en otro broker

El informe no es suficiente.

El FIFO y la regla de recompra deben calcularse de forma global para el contribuyente, no broker por broker.

---

### 20.5 Usé `--fx-mode favorable`

No lo uses para declarar.

Regenera con:

```bash
--fx-mode degiro
```

o, si lo has decidido conscientemente:

```bash
--fx-mode ecb
```

---

## 21. Checklist antes de presentar

Antes de presentar la declaración:

- [ ] He cargado todo el histórico necesario.
- [ ] He indicado `--history-end-date` real.
- [ ] El histórico cubre al menos dos meses después de la última venta con pérdida relevante.
- [ ] No tengo el mismo ISIN en otro broker.
- [ ] No hay FIFO incompleto.
- [ ] No hay eventos corporativos sin revisar.
- [ ] No he usado `--fx-mode favorable`.
- [ ] He revisado `03 Checks 2M`.
- [ ] He marcado el check solo en las líneas indicadas.
- [ ] Las casillas 0339 y 0340 cuadran con `04 Control Renta WEB`.
- [ ] He revisado si hay pérdidas diferidas de ejercicios anteriores.
- [ ] He conservado CSV originales, informe Markdown y Excel.

---

## 22. Ejemplos de uso

### 22.1 Informe estándar IRPF 2025

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28
```

Genera:

```text
informe_irpf_2025.md
informe_irpf_2025.xlsx
```

---

### 22.2 Indicando Excel explícitamente

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --fx-mode degiro --history-end-date 2026-02-28
```

---

### 22.3 Con pérdidas patrimoniales pendientes de años anteriores

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --carry-gains-losses 1250.45
```

---

### 22.4 Con rendimientos negativos pendientes de capital mobiliario

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --carry-income-losses 300
```

---

### 22.5 Con arrastres desde JSON

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --carryover-json carryovers.json
```

`carryovers.json`:

```json
{
  "income_losses": "300",
  "gains_losses": "1250.45"
}
```

---

### 22.6 Con estimación de doble imposición

```bash
python degiro_irpf.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --savings-tax-rate-hint 0.19
```

---

## 23. Estructura interna del cálculo

### 23.1 `Trade`

Representa una compra o venta del CSV de transacciones.

Campos clave:

```python
quantity
gross_eur
fee_eur
total_eur
side
isin
trade_dt
```

---

### 23.2 `Lot`

Representa un lote FIFO abierto.

Campos clave:

```python
quantity_open
unit_cost_eur
deferred_loss_unit_eur
deferred_source_year
```

---

### 23.3 `Disposal`

Representa una venta antes de transformarla en líneas fiscales F2.

Campos clave:

```python
proceeds_eur
cost_basis_eur
gain_loss_eur
blocked_loss_eur
replacement_quantity
fifo_complete
```

---

### 23.4 `F2Line`

Representa una línea fiscal para Renta WEB.

Es la capa más importante para evitar errores.

Campos clave:

```python
proceeds_eur
acquisition_eur
real_gain_loss_eur
non_computable_loss_eur
integrable_gain_loss_eur
check_two_month_rule
```

Una `Disposal` puede producir:

- una `F2Line`, si no hay incidencia;
- una `F2Line` con check, si toda la pérdida está bloqueada;
- dos `F2Line`, si solo parte de la pérdida está bloqueada.

---

## 24. Validaciones que realiza

El script valida que las líneas F2 cuadran con los `Disposal` originales:

```text
suma transmisión F2 = suma transmisión ventas
suma adquisición F2 = suma adquisición ventas
suma resultado integrable F2 = suma resultado integrable ventas
suma pérdida no computable F2 = suma pérdida bloqueada ventas
```

Si algo no cuadra, genera alerta crítica.

También genera alertas si:

- hay FIFO incompleto;
- hay `--history-end-date` incoherente;
- falta `--history-end-date`;
- hay operaciones BUY/SELL con el mismo timestamp;
- quedan pérdidas diferidas pendientes;
- se usa `fx-mode favorable`;
- hay eventos corporativos;
- hay pérdidas diferidas procedentes de ejercicios anteriores.

---

## 25. Tests recomendados

Antes de confiar en el script, conviene probar estos casos:

### Test 1: venta con pérdida sin recompra

```text
BUY 100 @ 10
SELL 100 @ 8
sin recompra posterior
```

Esperado:

```text
check 2M: NO
pérdida integrable: completa
pendiente final: 0
```

---

### Test 2: venta con pérdida totalmente bloqueada

```text
BUY 100 @ 10
SELL 100 @ 8
BUY 100 @ 7 dentro de 2 meses
```

Esperado:

```text
check 2M: SÍ
pérdida integrable inicial: 0
pérdida diferida en lote nuevo
```

---

### Test 3: venta parcialmente bloqueada

```text
pérdida real: -1.755,25
pérdida bloqueada: 1.176,01
pérdida computable: -579,24
```

Esperado:

```text
dos líneas F2:
- tramo no computable con check SÍ
- tramo computable con check NO
```

---

### Test 4: cierre completo sin recompra posterior

```text
compras
ventas hasta posición 0
sin recompra en 2 meses
```

Esperado:

```text
pérdida diferida pendiente final: 0
```

---

### Test 5: venta en diciembre y recompra en enero

```text
SELL con pérdida el 20/12/2025
BUY mismo ISIN el 10/01/2026
```

Esperado:

```text
pérdida bloqueada en 2025
lote de 2026 con pérdida diferida
```

---

### Test 6: FIFO incompleto

```text
SELL 100 sin compras previas cargadas
```

Esperado:

```text
alerta crítica
no aplicar automáticamente regla 2M
```

---

## 26. Referencias legales y fuentes

### BOE

Ley 35/2006 del IRPF:

- Artículo 33.5: pérdidas no computables por recompra.
- Artículo 37.2: FIFO para valores homogéneos.

URL:

```text
https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764
```

---

### Agencia Tributaria - acciones admitidas a negociación

Ayuda Renta WEB para ganancias y pérdidas patrimoniales derivadas de transmisiones de acciones admitidas a negociación.

URL:

```text
https://sede.agenciatributaria.gob.es/Sede/Ayuda/24Presentacion/100/7_6_6_2/ganancias_perdidas_patrimoniales_derivadas_acciones.html
```

---

### Agencia Tributaria - valores homogéneos

Ayuda de Cartera de Valores sobre valores homogéneos.

URL:

```text
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-ayuda-presentacion/cartera-valores/2-valores-homogeneos.html
```

---

### Banco Central Europeo - tipos de cambio de referencia

Tipos de cambio de referencia del euro.

URL:

```text
https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html
```

---

## Aviso final

Este script ayuda a estructurar la información, pero la responsabilidad de la declaración es del contribuyente.

Usa el informe como herramienta de control:

```text
CSV DEGIRO → Script → Markdown/Excel → Renta WEB → comprobación 0339/0340
```

No presentes sin revisar alertas críticas.