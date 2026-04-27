# Limitaciones, errores frecuentes y checklist

Esta herramienta ayuda a preparar la declaración, pero no convierte un histórico incompleto o un caso fiscal complejo en una respuesta automática fiable. Usa esta página como semáforo antes de copiar datos a Renta WEB.

## Semáforo rápido

Puedes usar el informe con relativa normalidad si:

- solo declaras acciones negociadas de DEGIRO;
- tienes todo el histórico necesario;
- no has operado el mismo ISIN en otros brokers;
- no hay eventos corporativos complejos sin revisar;
- no aparece FIFO incompleto;
- has revisado todos los checks 2M.

Necesitas revisión manual seria si:

- el mismo ISIN aparece en otro broker;
- faltan compras antiguas;
- hay splits, fusiones, spin-offs o cambios de ISIN;
- hay ventas en corto;
- la operación afecta a acciones no admitidas a negociación;
- estás usando el informe para algo distinto del apartado F2 de acciones.

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
- operaciones del mismo ISIN fuera de DEGIRO.

### El informe muestra check 2M pero pendiente final 0

Puede ser correcto. Significa que la pérdida estuvo bloqueada temporalmente, pero se liberó después al vender los lotes de sustitución.

### Sale FIFO incompleto

Significa que vendiste más títulos de los que el histórico cargado permite justificar. No uses el resultado como cifra final hasta cargar compras anteriores o revisar el caso manualmente.

### Tengo el mismo ISIN en otro broker

El informe de DEGIRO por sí solo no es suficiente. FIFO y regla de recompra deben calcularse de forma global para el contribuyente.

### Usé `--fx-mode favorable`

No lo uses para declarar. Regenera con `degiro` o, si has decidido conscientemente ese criterio, con `ecb`.

### Veo dividendos o retenciones

Úsalos como apoyo de revisión. La detección de doble imposición es heurística y debe comprobarse manualmente antes de trasladar cifras a Renta WEB.

## Checklist antes de presentar

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

## Checklist de éxito del proyecto

El proyecto ha cumplido su función si has podido:

- entender qué datos van a Renta WEB;
- detectar ventas afectadas por la regla de los 2 meses;
- evitar recalcular FIFO a mano;
- encontrar alertas antes de presentar;
- conservar un soporte claro para revisar la declaración.

Si has llegado a ese punto, dona para sostener el mantenimiento:

- [GitHub Sponsors](https://github.com/sponsors/flaviogrillo1)
- [Buy Me a Coffee](https://buymeacoffee.com/flaviogrillo)
- [Stripe](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)
