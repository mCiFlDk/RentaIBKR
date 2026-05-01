# Limitaciones, errores frecuentes y checklist

Esta herramienta ayuda a preparar la declaración, pero no convierte un histórico incompleto o un caso fiscal complejo en una respuesta automática fiable.

## Semáforo rápido

Puedes usar el informe con relativa normalidad si:

- solo declaras acciones negociadas de IBKR;
- has cargado todos los informes anuales necesarios;
- no has operado el mismo ISIN en otros brokers;
- no hay eventos corporativos complejos sin revisar;
- no aparece FIFO incompleto;
- has revisado todos los checks 2M.

Necesitas revisión manual seria si:

- el mismo ISIN aparece en otro broker;
- faltan informes de años anteriores;
- hay splits, fusiones, spin-offs o cambios de ISIN;
- hay ventas en corto;
- el instrumento no es una acción común o ADR;
- estás usando el informe para ETFs, ETCs, fondos, opciones, futuros, CFDs o cripto.

## Limitaciones conocidas

El script no resuelve automáticamente:

- mismo ISIN en otros brokers;
- ventas sin histórico completo;
- posiciones cortas o ventas en corto;
- préstamo de valores;
- acciones no admitidas a negociación si requieren ventana de 1 año;
- ETFs, fondos, criptomonedas, opciones, futuros, warrants o CFDs;
- derechos de suscripción, dividendos en acciones, acciones liberadas;
- splits, reverse splits, spin-offs, fusiones, cambios de ISIN y otras operaciones corporativas complejas;
- titularidades distintas o cuentas conjuntas.

## Errores frecuentes

### Renta WEB no cuadra con el informe

Revisa `04 Control Renta WEB`.

Si falla el cuadre, revisa especialmente:

- líneas con check 2M;
- ventas parcialmente bloqueadas;
- pérdidas introducidas como no computables completas cuando solo lo eran parcialmente;
- importes copiados con signo incorrecto;
- operaciones del mismo ISIN fuera de IBKR.

### El informe muestra check 2M pero pendiente final 0

Puede ser correcto. Significa que la pérdida estuvo bloqueada temporalmente, pero se liberó después al vender los lotes de sustitución.

### Sale FIFO incompleto

Significa que vendiste más títulos de los que el histórico cargado permite justificar. Carga informes anuales anteriores o revisa el caso manualmente.

### Tengo el mismo ISIN en otro broker

El informe de IBKR por sí solo no es suficiente. FIFO y regla de recompra deben calcularse de forma global para el contribuyente.

### Veo instrumentos no acción común

IBKR puede incluir ETFs/ETCs en secciones de acciones. El script los procesa para no romper el flujo, pero los marca para revisión manual.

### Veo dividendos o retenciones

Úsalos como apoyo de revisión. La detección de doble imposición es heurística y debe comprobarse manualmente antes de trasladar cifras a Renta WEB.

## Checklist antes de presentar

- [ ] He cargado todo el histórico necesario.
- [ ] He indicado `--history-end-date` real.
- [ ] El histórico cubre al menos dos meses después de la última venta con pérdida relevante.
- [ ] No tengo el mismo ISIN en otro broker.
- [ ] No hay FIFO incompleto.
- [ ] No hay eventos corporativos sin revisar.
- [ ] He revisado instrumentos no `COMMON`/`ADR`.
- [ ] He revisado `03 Checks 2M`.
- [ ] He marcado el check solo en las líneas indicadas.
- [ ] Las casillas 0339 y 0340 cuadran con `04 Control Renta WEB`.
- [ ] He revisado si hay pérdidas diferidas de ejercicios anteriores.
- [ ] He conservado CSV originales, informe Markdown y Excel.
