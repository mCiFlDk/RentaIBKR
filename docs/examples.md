# Ejemplos y demo

Esta página sirve para probar el flujo sin usar tus datos reales y para copiar comandos habituales.

## Demo local incluida en el repo

- [CSV de operaciones](../examples/demo_transactions.csv)
- [CSV de cuenta](../examples/demo_account.csv)
- [Informe Markdown generado](../examples/informe_demo.md)
- [Informe Excel generado](../examples/informe_demo.xlsx)

La demo visual está centrada en ventas de acciones para Renta WEB. Dividendos, intereses, retenciones y otros elementos calculados por el script no están representados en esas dos pantallas.

## Pantallas de referencia

![Pantalla resumen Renta WEB](../examples/assets/renta-web-resumen.svg)

![Pantalla alta transmisión Renta WEB](../examples/assets/renta-web-transmision.svg)

## Ejemplos de uso

### Informe estándar IRPF 2025

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28
```

### Indicando Excel explícitamente

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --fx-mode degiro --history-end-date 2026-02-28
```

### Con pérdidas patrimoniales pendientes de años anteriores

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --carry-gains-losses 1250.45
```

### Con rendimientos negativos pendientes de capital mobiliario

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --carry-income-losses 300
```

### Con arrastres desde JSON

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --carryover-json carryovers.json
```

### Con estimación de doble imposición

```bash
python main.py --transactions Transactions.csv --account Account.csv --year 2025 --output informe_irpf_2025.md --fx-mode degiro --history-end-date 2026-02-28 --savings-tax-rate-hint 0.19
```

## Casos recomendados para probar

1. Venta con pérdida sin recompra.
2. Venta con pérdida totalmente bloqueada.
3. Venta parcialmente bloqueada.
4. Cierre completo sin recompra posterior.
5. Venta en diciembre y recompra en enero.
6. FIFO incompleto.

## Qué revisar después de cada ejemplo

Después de ejecutar cualquier comando, abre el Excel y comprueba:

- `09 Alertas`: no debería haber riesgos sin revisar;
- `03 Checks 2M`: confirma qué líneas llevan check;
- `04 Control Renta WEB`: revisa el control agregado;
- `02 Renta WEB`: identifica las líneas que se copiarían en Renta WEB.

El ejemplo ha funcionado cuando entiendes por qué cada línea aparece como aparece. Ese es también el criterio de éxito con tus datos reales.

## Cierre del flujo

Si el proyecto te ahorra una revisión manual, te ayuda a detectar una recompra o te da un Excel claro para Renta WEB, cierra el flujo apoyando su mantenimiento:

- [GitHub Sponsors](https://github.com/sponsors/flaviogrillo1)
- [Buy Me a Coffee](https://buymeacoffee.com/flaviogrillo)
- [Stripe](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)
