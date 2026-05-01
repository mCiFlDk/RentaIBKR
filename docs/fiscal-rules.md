# Reglas fiscales y criterios

Esta página resume el criterio que sigue el script. Está escrita para entender el informe, no para sustituir una revisión fiscal profesional.

## FIFO

Para valores homogéneos, el script considera transmitidos primero los valores adquiridos primero.

En la práctica:

- las compras forman una cola por ISIN;
- cada venta consume primero las compras más antiguas;
- el coste de adquisición sale de los lotes consumidos;
- las comisiones de compra y venta se incorporan al cálculo cuando están disponibles.

## Informes IBKR de varios años

El FIFO solo es fiable si el script recibe todo el histórico necesario. Puedes pasar varios informes anuales con `--ibkr-report`.

Ejemplo:

```bash
python main.py --ibkr-report IBKR_2025.csv IBKR_2026.csv IBKR_2027.csv --year 2027 --output informe_2027.md --history-end-date 2027-12-31
```

## Valores homogéneos

El script usa el ISIN informado por IBKR como clave principal. Si IBKR no informa ISIN, usa el símbolo como fallback y genera un resultado que debe revisarse.

Requieren revisión manual:

- mismo ISIN en otro broker;
- titularidades distintas;
- ADR frente a acción ordinaria;
- clases distintas de acciones;
- cambios de ISIN;
- fusiones, spin-offs u otros eventos corporativos.

## Regla de los 2 meses

Para acciones admitidas a negociación, el modelo aplica por defecto una ventana de dos meses antes o después de la venta.

Cuando hay pérdida y recompra dentro de esa ventana, la pérdida puede quedar no computable en ese momento. El informe marca esas líneas para que sepas cuándo revisar el check de Renta WEB.

## Pérdidas diferidas

El modelo hace dos cosas:

1. bloquea la pérdida proporcional afectada por recompra;
2. la añade al coste fiscal del lote de sustitución para integrarla cuando ese lote se venda.

Por eso puedes ver un check 2M en una venta y, aun así, una pérdida pendiente final de 0 si después se vendieron los lotes de sustitución.

## Ventas parcialmente bloqueadas

Una misma venta puede tener una parte bloqueada y otra parte computable. En ese caso el informe separa líneas:

- una línea con check `SÍ` para la parte no computable;
- una línea con check `NO` para la parte computable.

## Tipo de cambio

IBKR informa operaciones en la divisa del activo. Para calcular valores fiscales en EUR, el script usa tipos históricos BCE/ECB para importes no EUR.

La primera ejecución con divisas no EUR descarga y cachea:

```text
.cache/ecb_hist.xml
```

## Dividendos y doble imposición

La doble imposición se detecta de forma heurística a partir de la descripción de dividendos y retenciones de IBKR. Usa esa sección como apoyo de revisión, no como cifra final automática.

## Compensaciones de la base del ahorro

El script estima compensaciones entre:

- ganancias y pérdidas patrimoniales;
- rendimientos del capital mobiliario;
- arrastres de ejercicios anteriores.

Es una estimación orientativa. Debe usarse como control, no como sustituto del cálculo automático de Renta WEB.

## Fuentes oficiales

- [Ley 35/2006 del IRPF - BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764)
- [AEAT - valores homogéneos](https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-ayuda-presentacion/cartera-valores/2-valores-homogeneos.html)
- [AEAT - Renta WEB F2](https://sede.agenciatributaria.gob.es/Sede/Ayuda/24Presentacion/100/7_6_6_2/ganancias_perdidas_patrimoniales_derivadas_acciones.html)
