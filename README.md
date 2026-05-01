<div align="center">

# RentaIBKR

### Prepara Renta WEB desde informes anuales CSV de Interactive Brokers

IBKR Annual Activity CSV · FIFO · Regla de recompra · Líneas F2 · Markdown + Excel

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-2457ff?style=for-the-badge&logo=gnu&logoColor=white)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Markdown report](https://img.shields.io/badge/Output-Markdown-111111?style=for-the-badge&logo=markdown&logoColor=white)](docs/usage.md#salidas)
[![Excel report](https://img.shields.io/badge/Output-Excel-217346?style=for-the-badge&logo=microsoft-excel&logoColor=white)](docs/usage.md#salidas)

</div>

> Proyecto no oficial. No está afiliado, aprobado ni respaldado por Interactive Brokers, la Agencia Tributaria ni ninguna administración pública.

RentaIBKR convierte uno o varios informes anuales CSV de Interactive Brokers en un informe pensado para declarar ventas de acciones en Renta WEB. Reconstruye FIFO por ISIN, aplica la regla de recompra de valores homogéneos, marca las líneas F2 que requieren check y genera un Markdown y un Excel revisables.

## Para quién es

Úsalo si:

- operas acciones en Interactive Brokers y quieres preparar el apartado F2 de Renta WEB;
- necesitas juntar varios años de informes IBKR para conservar FIFO completo;
- compraste activos en un año y puedes venderlos en ejercicios posteriores;
- quieres detectar pérdidas afectadas por la regla de recompra de 2 meses;
- quieres un Excel operativo para copiar datos y revisar el cuadre.

No lo uses como resultado automático si tu caso depende de ETFs, ETCs, fondos, cripto, opciones, futuros, CFDs, ventas en corto o eventos corporativos complejos. IBKR puede agrupar algunos productos como `Acciones`; el informe los marca para revisión cuando el tipo de instrumento no es acción común/ADR.

## Uso rápido

Requisitos:

- Python 3.11 o superior.
- Uno o varios CSV de informe anual de Interactive Brokers.
- Historial suficiente para cubrir compras antiguas y recompras posteriores.
- Conexión a internet la primera vez que se necesiten tipos de cambio BCE/ECB para divisas no EUR.

Comando recomendado para IRPF 2025:

```bash
python main.py --ibkr-report IBKR_2025.csv --year 2025 --output informe_irpf_2025.md --excel-output informe_irpf_2025.xlsx --history-end-date 2025-12-31
```

Si tienes varios años, pásalos todos:

```bash
python main.py --ibkr-report IBKR_2025.csv IBKR_2026.csv IBKR_2027.csv --year 2027 --output informe_irpf_2027.md --history-end-date 2027-12-31
```

Si no indicas `--excel-output`, el script genera automáticamente un Excel con el mismo nombre base que el Markdown.

## Qué devuelve

- Markdown: explicación legible, resumen ejecutivo, líneas F2, checks 2M, control de casillas, pérdidas diferidas, compensaciones y alertas.
- Excel: pestañas operativas para trabajar en Renta WEB sin perder el rastro de cada cifra.

Pestañas clave:

| Pestaña | Para qué sirve |
|---|---|
| `02 Renta WEB` | Líneas que normalmente copiarás en Renta WEB |
| `03 Checks 2M` | Ventas donde debes revisar la regla de recompra |
| `04 Control Renta WEB` | Cuadre agregado con 0339/0340 |
| `09 Alertas` | Riesgos que conviene resolver antes de presentar |
| `10 Resumen final` | Bloque corto para repasar el resultado |

## Demo local

Puedes probar el flujo sin datos reales:

```bash
python main.py --ibkr-report examples/demo_ibkr_2025.csv --year 2025 --output examples/informe_demo.md --excel-output examples/informe_demo.xlsx --history-end-date 2026-02-28
```

Archivos incluidos:

- [CSV anual IBKR demo](examples/demo_ibkr_2025.csv)
- [Informe Markdown generado](examples/informe_demo.md)
- [Informe Excel generado](examples/informe_demo.xlsx)

## Documentación

Lee estos documentos en este orden:

1. [Uso y argumentos](docs/usage.md)
2. [Cómo trasladar los datos a Renta WEB](docs/renta-web.md)
3. [Limitaciones, errores frecuentes y checklist](docs/limitations.md)
4. [Reglas fiscales y criterios](docs/fiscal-rules.md)
5. [Ejemplos y demo](docs/examples.md)

## Fuentes oficiales

La base normativa principal es la Ley 35/2006 del IRPF, artículos 33.5 y 37.2.

- [Ley 35/2006 del IRPF - BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764)
- [AEAT - valores homogéneos](https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-ayuda-presentacion/cartera-valores/2-valores-homogeneos.html)
- [AEAT - Renta WEB F2](https://sede.agenciatributaria.gob.es/Sede/Ayuda/24Presentacion/100/7_6_6_2/ganancias_perdidas_patrimoniales_derivadas_acciones.html)

## Disclaimer

Esta herramienta es de apoyo. No sustituye a Renta WEB ni a un asesor fiscal.

- Los importes no EUR se convierten con tipos históricos BCE/ECB.
- La doble imposición se detecta de forma heurística por descripción del movimiento.
- Las compensaciones de la base del ahorro son una estimación orientativa.
- La responsabilidad final de la declaración es del contribuyente.

Licencia: [LICENSE](LICENSE).
