# Informe IRPF 2025 - DEGIRO

## 1. Resumen ejecutivo

| Concepto | Importe / Estado | Acción |
| --- | ---: | --- |
| Resultado F2 integrable antes de compensaciones | 214.00 EUR | Meter en Renta WEB |
| Valor total de transmisión | 2437.00 EUR | Informar en F2 |
| Valor total de adquisición | 2344.20 EUR | Informar en F2 |
| Pérdidas no computables por regla 2 meses generadas en 2025 | 121.20 EUR | Marcar check solo en las líneas afectadas |
| Pérdidas diferidas de ventas anteriores integradas en 2025 | 121.20 EUR | Verificar si proceden del mismo ejercicio o de ejercicios anteriores |
| Pérdida diferida pendiente a 31/12/2025 | 0.00 EUR | Si es 0, no queda pérdida bloqueada al cierre |
| Pérdida diferida pendiente al final del histórico cargado | 0.00 EUR | Si es 0, no queda pérdida pendiente según el histórico |
| Dividendos brutos | 12.50 EUR | Capital mobiliario, si aplica |
| Retención extranjera asociada | 1.90 EUR | Doble imposición, si aplica |
| Intereses | 0.35 EUR | Capital mobiliario, si aplica |

- Pérdidas compensables: NO. Resultado F2 integrable actual: 214.00 EUR.
- Pérdidas bloqueadas pendientes: cierre 0.00 EUR; final histórico 0.00 EUR.
- Líneas con check de regla de 2 meses: SÍ.
- Crítico antes de presentar: NO detectado.

## 2. Qué meter en Renta WEB

| Activo | ISIN | Fecha / Grupo | Transmisión EUR | Adquisición EUR | Resultado real | Pérdida no computable 2M | ¿Marcar check recompra? | Resultado integrable | Acción en Renta WEB |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| DEMO BIOTECH INC | US1234567890 | 20/02/2025 15:45 · tramo computable | 319.60 EUR | 400.40 EUR | -80.80 EUR | 0.00 EUR | NO | -80.80 EUR | Alta F2 normal; tramo computable de venta con recompra |
| DEMO BIOTECH INC | US1234567890 | 20/02/2025 15:45 · tramo no computable | 479.40 EUR | 600.60 EUR | -121.20 EUR | 121.20 EUR | SÍ | 0.00 EUR | Alta F2 con check de recompra; tramo no computable |
| DEMO BIOTECH INC | US1234567890 | 20/06/2025 16:00 | 719.00 EUR | 542.20 EUR | 176.80 EUR | 0.00 EUR | NO | 176.80 EUR | Alta F2 normal; Integra diferido |
| DEMO ENERGY PLC | GB1234567890 | Agrupado sin incidencias | 919.00 EUR | 801.00 EUR | 118.00 EUR | 0.00 EUR | NO | 118.00 EUR | Alta F2 normal |

### Checks de regla de 2 meses

| Fecha | Activo | ISIN | Pérdida real | Pérdida no computable | Motivo |
| --- | --- | --- | ---: | ---: | --- |
| 20/02/2025 15:45 · tramo no computable | DEMO BIOTECH INC | US1234567890 | 121.20 EUR | 121.20 EUR | Venta dividida para Renta WEB. Tramo no computable por recompra homogénea dentro de 2 meses; 60 títulos afectados. |

## 3. Control casillas Renta WEB

| Concepto | Importe |
| --- | ---: |
| Suma ganancias integrables acciones negociadas | 294.80 EUR |
| Suma pérdidas integrables acciones negociadas | 80.80 EUR |
| Resultado neto integrable F2 | 214.00 EUR |
| Pérdidas no computables por regla 2M | 121.20 EUR |

No queda pérdida diferida pendiente al final del histórico cargado.

## 4. Validación de pérdidas diferidas

| Activo | ISIN | Pérdida diferida generada | Pérdida diferida integrada | Pendiente 31/12 | Pendiente final histórico | Conclusión |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| DEMO ENERGY PLC | GB1234567890 | 0.00 EUR | 0.00 EUR | 0.00 EUR | 0.00 EUR | Liberada completamente |
| DEMO BIOTECH INC | US1234567890 | 121.20 EUR | 121.20 EUR | 0.00 EUR | 0.00 EUR | Liberada completamente |

## 5. Compensaciones base del ahorro

| Concepto | Importe |
| --- | ---: |
| Saldo ganancias/pérdidas patrimoniales F2 antes de compensaciones | 214.00 EUR |
| Saldo capital mobiliario antes de compensaciones | 10.85 EUR |
| Compensación aplicada entre bloques del ejercicio | 0.00 EUR |
| Arrastres de años anteriores usados | 0.00 EUR |
| Saldo final F2 estimado por el script | 214.00 EUR |
| Saldo final capital mobiliario estimado | 10.85 EUR |

Usar como control, no como sustituto del cálculo automático de Renta WEB.

- Pérdida patrimonial compensable: NO.
- Compensación con capital mobiliario: NO.
- Saldo negativo para arrastrar: NO.

## 6. Dividendos, retenciones y doble imposición

| Concepto | Importe EUR | Dónde va |
| --- | ---: | --- |
| Dividendos brutos | 12.50 EUR | Capital mobiliario |
| Intereses | 0.35 EUR | Capital mobiliario |
| Retención extranjera asociada | 1.90 EUR | Deducción doble imposición internacional; estimación heurística |
| Renta extranjera asociada | 12.50 EUR | Deducción doble imposición internacional; estimación heurística |

La doble imposición se detecta de forma heurística por descripción del movimiento. Revisa manualmente dividendos y retenciones antes de trasladarlos a Renta WEB.

## 7. Insights fiscales importantes

- Hay líneas con check 2M, pero la pérdida diferida pendiente final es 0; el bloqueo fue temporal y toda la pérdida diferida quedó liberada después.
- El control de casillas F2 debe hacerse con las líneas fiscales F2, no con cada Disposal bruto: una venta parcialmente bloqueada puede dividirse en un tramo no computable con check y otro tramo computable sin check.

## 8. Alertas críticas antes de presentar

No se detectan alertas críticas en el informe proporcionado.

## 9. Resumen final para copiar a mano

```text
F2 acciones:
- Transmisión total: 2437.00 EUR
- Adquisición total: 2344.20 EUR
- Resultado integrable antes de compensaciones: 214.00 EUR
- Líneas con check regla 2 meses: SÍ
- Pérdida diferida pendiente final: 0.00 EUR

Capital mobiliario:
- Dividendos/intereses brutos: 12.85 EUR
- Gastos deducibles: 2.00 EUR
- Retención extranjera asociada: 1.90 EUR

Conclusión:
Sin bloqueos finales pendientes ni alertas críticas de presentación.
```
