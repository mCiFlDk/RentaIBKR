# Ejemplos y demo

Esta página sirve para probar el flujo sin usar tus datos reales y para copiar comandos habituales.

## Demo local incluida

- [CSV anual IBKR demo](../examples/demo_ibkr_2025.csv)
- [Informe Markdown generado](../examples/informe_demo.md)
- [Informe Excel generado](../examples/informe_demo.xlsx)

Ejecuta:

```bash
python main.py --ibkr-report examples/demo_ibkr_2025.csv --year 2025 --output examples/informe_demo.md --excel-output examples/informe_demo.xlsx --history-end-date 2026-02-28
```

## Ejemplos de uso

### Informe estándar IRPF 2025

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --history-end-date 2025-12-31
```

### Indicando Excel explícitamente

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --history-end-date 2025-12-31
```

### Con varios informes anuales

```bash
python main.py --ibkr-report IBKR_2025.csv IBKR_2026.csv IBKR_2027.csv --year 2027 --output informe_irpf_2027.md --history-end-date 2027-12-31
```

### Con pérdidas patrimoniales pendientes

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --history-end-date 2025-12-31 --carry-gains-losses 1250.45
```

### Con rendimientos negativos pendientes de capital mobiliario

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --history-end-date 2025-12-31 --carry-income-losses 300
```

### Con arrastres desde JSON

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --history-end-date 2025-12-31 --carryover-json carryovers.json
```

### Con estimación de doble imposición

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --history-end-date 2025-12-31 --savings-tax-rate-hint 0.19
```

## Casos recomendados para probar

1. Venta con pérdida sin recompra.
2. Venta con pérdida totalmente bloqueada.
3. Venta parcialmente bloqueada.
4. Cierre completo sin recompra posterior.
5. Venta en diciembre y recompra en enero.
6. FIFO incompleto por no cargar años anteriores.

## Qué revisar después de cada ejemplo

Abre el Excel y comprueba:

- `09 Alertas`;
- `03 Checks 2M`;
- `04 Control Renta WEB`;
- `02 Renta WEB`.
