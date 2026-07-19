# Cómo conectar Claude Haiku como motor OCR

Claude Haiku es un motor OCR alternativo a Tesseract. Es un servicio pago de Anthropic: cada imagen transcrita consume la cuota de la API key correspondiente. El costo depende del pricing vigente de Anthropic; conviene revisarlo en [anthropic.com/pricing](https://www.anthropic.com/pricing) antes de usar este motor.

## 1. Obtener una API key de Anthropic

1. Ingresar a [console.anthropic.com](https://console.anthropic.com/) y crear una cuenta o iniciar sesión.
2. Cargar un método de pago en la sección de facturación (billing), ya que el uso de la API se cobra por consumo.
3. En la sección de API Keys, generar una nueva key. Su formato empieza con `sk-ant-`.
4. Copiar la key. Anthropic solo la muestra una vez; si se pierde, es necesario generar una nueva.

## 2. Cargar la key en la aplicación

1. Abrir la aplicación e ingresar a **Configuración** (ícono de engranaje en el menú lateral).
2. En **Motor OCR**, seleccionar **Claude Haiku**.
3. La aplicación solicitará la API key en un cuadro de diálogo. Pegarla ahí y confirmar.

Si ese cuadro se cerró sin cargar la key, también es posible hacerlo desde el campo **API key de Anthropic** que aparece debajo del selector de motor: escribir la key y presionar **Guardar**.

## 3. Qué sucede con la key

- La key se guarda de forma segura en el keyring del sistema operativo (no se guarda en `config.json` ni en ningún archivo del proyecto).
- Una vez guardada, el campo se muestra enmascarado (`••••••••••••`) y el botón cambia a **Cambiar**, por si es necesario reemplazarla.
- Si el sistema no puede guardar la key en el keyring (por ejemplo, por falta de permisos), la aplicación muestra un mensaje de error y vuelve a seleccionar Tesseract como motor.

## 4. Usar Claude Haiku

Con la key cargada, seleccionar **Claude Haiku** en Configuración e ir a la vista **OCR de imágenes**: las transcripciones a partir de ese momento se realizan con Claude en lugar de Tesseract. Para volver a Tesseract, basta con elegirlo nuevamente en el mismo selector.

## Notas

- El motor Claude Haiku es exclusivo de la vista **OCR de imágenes**. El **OCR en vivo** siempre usa Tesseract.
- Si la API key no tiene saldo o es inválida, la aplicación mostrará el mensaje de error que devuelve la API de Anthropic.
