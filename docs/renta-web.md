# Cómo trasladar los datos a Renta WEB

Esta guía explica qué mirar en el Excel y cómo convertirlo en entradas manuales dentro de Renta WEB.

## Ruta dentro de Renta WEB

La ganancia o pérdida por venta de acciones se introduce en:

```text
Ganancias y pérdidas patrimoniales derivadas de la transmisión de elementos patrimoniales
(a integrar en la base imponible del ahorro)
→ Ganancias y pérdidas patrimoniales derivadas de la transmisión de acciones negociadas
```

La secuencia práctica suele ser:

```text
Acciones transmitidas y titulares
→ Importe global de las transmisiones efectuadas en 20XX
→ Transmisión de acciones negociadas
```

Pantallas de referencia:

![Pantalla resumen Renta WEB](../examples/assets/renta-web-resumen.svg)

![Pantalla alta transmisión Renta WEB](../examples/assets/renta-web-transmision.svg)

## Antes de copiar nada

Abre el Excel y revisa en este orden:

1. `09 Alertas`: si hay FIFO incompleto, histórico insuficiente o eventos raros, resuélvelo antes de seguir.
2. `03 Checks 2M`: identifica ventas afectadas por recompra de valores homogéneos.
3. `04 Control Renta WEB`: úsalo como control agregado para 0339/0340.
4. `02 Renta WEB`: usa esta pestaña como fuente principal para copiar datos.

## Campos que importan

En la ventana individual de Renta WEB interesan estos campos:

- entidad emisora;
- valor de transmisión;
- valor de adquisición;
- check de no imputación de pérdidas por recompra de valores homogéneos.

## Mapeo desde el Excel

| Salida del script | Campo en Renta WEB | Qué significa |
|---|---|---|
| `02 Renta WEB` | `Transmisión de acciones negociadas` | Tabla operativa principal |
| `Activo` | `Entidad emisora` | Nombre de la empresa |
| `Transmisión EUR` | `Valor de transmisión` | Neto de comisiones de venta |
| `Adquisición EUR` | `Valor de adquisición` | Coste FIFO con comisiones de compra |
| `¿Marcar check recompra?` | `No imputación de pérdidas por recompra de valores homogéneos` | Marca la casilla solo si dice `SÍ` |
| `Resultado integrable` | Control | Te ayuda a comprobar que la línea tiene sentido |
| `04 Control Renta WEB` | Casillas 0339/0340 | Control agregado |

## Introducción individual

Si tienes pocas ventas, normalmente es más claro introducirlas una a una.

Pasos:

1. Copia `Activo` en entidad emisora.
2. Copia `Adquisición EUR` en valor de adquisición.
3. Copia `Transmisión EUR` en valor de transmisión.
4. Marca el check de recompra solo cuando `¿Marcar check recompra?` diga `SÍ`.
5. Guarda y pasa a la siguiente línea.

Regla práctica:

```text
el script ya deja adquisición y transmisión en formato utilizable;
no recalcules comisiones a mano salvo que estés corrigiendo un caso detectado en alertas
```

## Ventas parcialmente bloqueadas

Cuando una venta tiene una pérdida parcialmente no computable por recompra, el script la divide en dos líneas F2:

- tramo no computable con check `SÍ`;
- tramo computable con check `NO`.

Esto evita que Renta WEB excluya toda la pérdida cuando solo una parte debía quedar bloqueada.

## Control de casillas

Usa `04 Control Renta WEB` como referencia:

- suma de ganancias integrables de acciones negociadas: control de la casilla 0339;
- suma de pérdidas integrables de acciones negociadas: control de la casilla 0340.

Si no cuadra, revisa en este orden:

1. líneas con check 2M;
2. ventas parcialmente bloqueadas;
3. FIFO incompleto;
4. importes introducidos a mano;
5. mismo ISIN comprado o vendido en otro broker.

## Señal de que puedes avanzar

Puedes pasar a la declaración cuando:

- has revisado todas las alertas;
- sabes qué líneas llevan check y cuáles no;
- las cifras agregadas te sirven para controlar 0339/0340;
- entiendes qué partes del informe son estimaciones de apoyo.

Cuando el informe ya te ha permitido completar esa revisión, el cierre recomendado es apoyar el proyecto:

- [GitHub Sponsors](https://github.com/sponsors/flaviogrillo1)
- [Buy Me a Coffee](https://buymeacoffee.com/flaviogrillo)
- [Stripe](https://donate.stripe.com/6oUeVebYc4Tc8sMgVqbbG00)
