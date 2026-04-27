# Reglas fiscales y criterios

Esta página resume el criterio que sigue el script. Está escrita para entender el informe, no para sustituir una revisión fiscal profesional.

## FIFO

Para valores homogéneos, el script considera transmitidos primero los valores adquiridos primero.

En la práctica:

- las compras forman una cola por ISIN;
- cada venta consume primero las compras más antiguas;
- el coste de adquisición sale de los lotes consumidos;
- las comisiones de compra y venta se incorporan al cálculo cuando están disponibles.

## Valores homogéneos

El script usa el ISIN como clave principal. Aun así, hay casos que requieren revisión manual:

- titularidades distintas;
- ADR frente a acción ordinaria;
- clases distintas de acciones;
- cambios de ISIN;
- fusiones, spin-offs u otros eventos corporativos.

Si has comprado el mismo ISIN en otro broker, el resultado de este proyecto no basta por sí solo: FIFO debe calcularse con todas tus operaciones.

## Regla de los 2 meses

Para acciones admitidas a negociación, el modelo aplica por defecto una ventana de:

```text
2 meses antes o después de la venta
```

Cuando hay pérdida y recompra dentro de esa ventana, la pérdida puede quedar no computable en ese momento. El informe marca esas líneas para que sepas cuándo revisar el check de Renta WEB.

## Pérdidas diferidas

El modelo hace dos cosas:

1. bloquea la pérdida proporcional afectada por recompra;
2. la añade al coste fiscal del lote de sustitución para integrarla cuando ese lote se venda.

Por eso puedes ver un check 2M en una venta y, aun así, una pérdida pendiente final de 0 si después se vendieron los lotes de sustitución.

## Ventas parcialmente bloqueadas

Una misma venta puede tener una parte bloqueada y otra parte computable. En ese caso el informe separa líneas para que puedas introducir en Renta WEB:

- una línea con check `SÍ` para la parte no computable;
- una línea con check `NO` para la parte computable.

Esta separación es una de las partes más útiles del Excel: evita tratar toda la pérdida como bloqueada cuando solo lo está una fracción.

## Doble imposición internacional

La doble imposición se detecta de forma heurística a partir de la descripción de los movimientos y del vínculo aproximado entre dividendos, retenciones e ISIN no españoles.

Úsalo como estimación y revisa manualmente dividendos y retenciones antes de trasladarlos a Renta WEB.

## Compensaciones de la base del ahorro

El script estima compensaciones entre:

- ganancias y pérdidas patrimoniales;
- rendimientos del capital mobiliario;
- arrastres de ejercicios anteriores.

Es una estimación orientativa. Debe usarse como control, no como sustituto del cálculo automático de Renta WEB.

## Tipo de cambio

`degiro` suele ser el modo más práctico para declarar porque usa los importes en EUR liquidados por el broker cuando existen.

`ecb` sirve como criterio externo y uniforme para comprobación.

`favorable` es una comparación técnica y no un criterio fiscal estable para presentar.

## Fuentes oficiales

La base normativa principal es la Ley 35/2006 del IRPF, artículos 33.5 y 37.2.

- [Ley 35/2006 del IRPF - BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764)
- [AEAT - valores homogéneos](https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-ayuda-presentacion/cartera-valores/2-valores-homogeneos.html)
- [AEAT - Renta WEB F2](https://sede.agenciatributaria.gob.es/Sede/Ayuda/24Presentacion/100/7_6_6_2/ganancias_perdidas_patrimoniales_derivadas_acciones.html)

## Cierre recomendado

Cuando estas reglas te permitan entender el informe y trasladar los datos con menos incertidumbre, el proyecto ha hecho su trabajo. Apoyarlo con una donación ayuda a mantener reglas, ejemplos y documentación actualizados:

- [GitHub Sponsors](https://github.com/sponsors/flaviogrillo1)
- [Buy Me a Coffee](https://buymeacoffee.com/flaviogrillo)
- [Stripe](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)
