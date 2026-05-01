# Uso y argumentos

Esta guía explica el recorrido completo con informes anuales CSV de Interactive Brokers.

## Requisitos

- Python 3.11 o superior.
- Uno o varios informes anuales de actividad de Interactive Brokers en CSV.
- Historial suficiente para cubrir todas las compras necesarias para las ventas del ejercicio.
- Conexión a internet la primera vez que se necesiten tipos de cambio BCE/ECB.

El script sigue usando solo librerías estándar de Python.

## Flujo recomendado

1. Exporta de IBKR todos los informes anuales necesarios.
2. Pasa al script todos los años que puedan afectar al FIFO del ejercicio.
3. Indica `--history-end-date` con la última fecha cubierta por el histórico cargado.
4. Abre primero el Excel, especialmente `09 Alertas`, `03 Checks 2M` y `04 Control Renta WEB`.
5. Corrige cualquier problema de histórico antes de copiar importes a Renta WEB.
6. Introduce las líneas de `02 Renta WEB`.
7. Conserva CSV, Markdown y Excel junto con la documentación de la declaración.

## Archivo de entrada IBKR

El script espera el CSV de informe anual de actividad de Interactive Brokers. En español, las secciones relevantes son:

| Sección IBKR | Uso |
|---|---|
| `Operaciones` | Compras y ventas de acciones |
| `Información de instrumento financiero` | Mapa símbolo → ISIN, descripción y tipo |
| `Dividendos` | Dividendos cobrados |
| `Retención de impuestos` | Retenciones vinculadas a dividendos |
| `Tarifas` | Gastos y comisiones de servicio |

Las filas de `Fórex` se ignoran para F2 de acciones. Los importes de acciones no EUR se convierten a EUR con BCE/ECB.

## Uso rápido

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --history-end-date 2025-12-31
```

Con varios años:

```bash
python main.py --ibkr-report IBKR_2025.csv IBKR_2026.csv IBKR_2027.csv --year 2027 --output informe_irpf_2027.md --history-end-date 2027-12-31
```

## Argumentos

### `--ibkr-report`

Ruta o rutas a informes anuales CSV de IBKR. Es obligatorio. También acepta el alias `--report`.

Pasa todos los informes que formen el histórico necesario. Si compraste en 2025 y vendes en 2030, el cálculo de 2030 debe recibir también los informes desde 2025.

### `--year`

Ejercicio fiscal que quieres analizar.

### `--output`

Ruta del informe Markdown. Si no se indica, el informe se imprime por consola.

### `--excel-output`

Ruta del Excel de salida. Si no se indica pero sí `--output`, se genera automáticamente un `.xlsx` con el mismo nombre base.

### `--history-end-date`

Fecha final cubierta por el histórico exportado. Formato `YYYY-MM-DD`.

Para ventas con pérdida de noviembre o diciembre, conviene cubrir al menos hasta febrero del año siguiente, porque la regla de recompra mira dos meses después de la venta.

### `--carry-gains-losses`

Pérdidas patrimoniales de ejercicios anteriores pendientes de compensar.

### `--carry-income-losses`

Rendimientos negativos del capital mobiliario de ejercicios anteriores pendientes de compensar.

### `--carryover-json`

Permite introducir arrastres desde un JSON con claves `income_losses` y `gains_losses`.

### `--savings-tax-rate-hint`

Tipo orientativo para estimar la deducción por doble imposición internacional. Úsalo como apoyo de revisión, no como cifra final automática.

## Salidas

### Markdown

Incluye resumen ejecutivo, líneas F2, checks de la regla de 2 meses, control de casillas, pérdidas diferidas, compensaciones, dividendos, retenciones, insights y alertas.

### Excel

Pestañas generadas:

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
- sabes qué importes vas a copiar y cuáles son solo estimaciones de apoyo;
- has guardado los CSV originales y los informes generados.
