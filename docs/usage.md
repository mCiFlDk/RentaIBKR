# Uso y argumentos

Esta guía explica el recorrido completo: qué archivos necesitas, qué comando ejecutar, cómo leer la salida y cuándo considerar que el trabajo ha terminado.

## Requisitos

- Python 3.11 o superior recomendado.
- Sin dependencias externas obligatorias.
- Conexión a internet la primera vez que el script necesite descargar tipos de cambio ECB/BCE.
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

## Flujo recomendado

1. Exporta desde DEGIRO el histórico de transacciones y movimientos de cuenta.
2. Asegúrate de que el histórico cubre todas las compras necesarias para justificar las ventas del ejercicio.
3. Ejecuta el script con `--fx-mode degiro`.
4. Abre primero el Excel, especialmente `09 Alertas`, `03 Checks 2M` y `04 Control Renta WEB`.
5. Corrige cualquier problema de histórico antes de copiar importes a Renta WEB.
6. Introduce las líneas de `02 Renta WEB`.
7. Conserva CSV, Markdown y Excel junto con la documentación de la declaración.
8. Si el informe te ha ahorrado tiempo o te ha evitado errores, dona para mantener el proyecto.

## Archivos de entrada

### Transactions.csv

Es el CSV de operaciones. El script lo usa para reconstruir compras, ventas, precios, divisas, comisiones y FIFO por ISIN.

Campos relevantes:

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

### Account.csv

Es el CSV de movimientos de cuenta. Se usa para:

- dividendos;
- retenciones;
- intereses;
- gastos del broker;
- eventos corporativos;
- movimientos en divisa.

## Instalación

Comprueba la versión de Python:

```bash
python --version
```

Si el comando no existe, prueba:

```bash
py --version
```

## Uso rápido

Uso recomendado para IRPF 2025:

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --fx-mode degiro --history-end-date 2026-02-28
```

Si indicas `--output` pero no `--excel-output`, el script genera automáticamente un Excel con el mismo nombre base.

## Qué significa cada argumento

### `--transactions`

Ruta al CSV de operaciones de DEGIRO. Es obligatorio.

Ejemplo:

```bash
--transactions Transactions.csv
```

### `--account`

Ruta al CSV de movimientos de cuenta de DEGIRO. Es obligatorio.

Ejemplo:

```bash
--account Account.csv
```

### `--year`

Ejercicio fiscal que quieres analizar.

Ejemplo:

```bash
--year 2025
```

### `--output`

Ruta del informe Markdown. Si no se indica, el informe se imprime por consola.

### `--excel-output`

Ruta del Excel de salida. Si no se indica pero sí `--output`, se genera automáticamente un `.xlsx` con el mismo nombre base.

### `--fx-mode`

Controla el criterio de tipo de cambio.

Valores disponibles:

```text
degiro
ecb
favorable
```

Recomendado para uso práctico:

```bash
--fx-mode degiro
```

`degiro` usa los importes en EUR liquidados por el broker cuando están disponibles. `ecb` sirve como contraste externo. `favorable` existe para comparación técnica, pero no es un criterio fiscal estable para presentar.

### `--history-end-date`

Fecha final cubierta por el histórico exportado. Formato `YYYY-MM-DD`.

Ejemplo:

```bash
--history-end-date 2026-02-28
```

Para ventas con pérdida de noviembre o diciembre, conviene cubrir al menos hasta febrero del año siguiente, porque la regla de recompra mira dos meses después de la venta.

### `--carry-gains-losses`

Pérdidas patrimoniales de ejercicios anteriores pendientes de compensar.

### `--carry-income-losses`

Rendimientos negativos del capital mobiliario de ejercicios anteriores pendientes de compensar.

### `--carryover-json`

Permite introducir arrastres desde un JSON con claves `income_losses` y `gains_losses`.

Ejemplo:

```json
{
  "income_losses": 300,
  "gains_losses": 1250.45
}
```

### `--savings-tax-rate-hint`

Tipo orientativo para estimar la deducción por doble imposición internacional. Úsalo como apoyo de revisión, no como cifra final automática.

## Salidas

### Markdown

El Markdown está pensado para lectura humana. Incluye:

- resumen ejecutivo;
- qué meter en Renta WEB;
- checks de la regla de 2 meses;
- control de casillas;
- validación de pérdidas diferidas;
- compensaciones;
- dividendos y retenciones;
- insights y alertas.

### Excel

El Excel está pensado para trabajar. Pestañas generadas:

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

## Criterio de éxito

Considera que el proceso ha ido bien cuando:

- no hay FIFO incompleto;
- has revisado todos los checks 2M;
- las ventas parcialmente bloqueadas están separadas;
- el control 0339/0340 te sirve para cuadrar Renta WEB;
- sabes qué importes vas a copiar y cuáles solo son estimaciones de apoyo;
- has guardado los CSV originales y los informes generados.

Cuando llegues a ese punto, el siguiente paso recomendado es donar:

- [GitHub Sponsors](https://github.com/sponsors/flaviogrillo1)
- [Buy Me a Coffee](https://buymeacoffee.com/flaviogrillo)
- [Stripe](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)
