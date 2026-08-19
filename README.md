# AC garrafa monitor

Apaga los splits Mitsubishi por MELCloud (apagado limpio) cuando la boya de
la garrafa de condensados se activa, en vez de cortar la corriente con el
Shelly. Solo corta el relé como fallback si MELCloud no responde a tiempo.
Al vaciar la garrafa, reenciende únicamente los splits que estaban
encendidos antes del corte.

## 1. Crear el repositorio

Sube este contenido a un repositorio **nuevo y público** en GitHub (público
para tener minutos de Actions ilimitados con un cron cada 5 min; en uno
privado el free tier de 2.000 min/mes se agotaría enseguida con este ritmo
de sondeo). Ningún secreto queda expuesto por ser público: las claves viven
como *Secrets*, cifradas, y nunca se imprimen en el código ni en los logs.

## 2. Activar Shelly Cloud

En la app de Shelly, entra en el dispositivo 1PM → Settings → Input/Output
y cambia el modo del SW a **Detached** (así la boya deja de cortar el relé
directamente).

Comprueba también que el "Cloud Control" del dispositivo está activado
(si ya lo controlas desde la app fuera de casa, ya lo tienes).

## 3. Secrets a configurar (Settings → Secrets and variables → Actions)

| Secret | De dónde sacarlo |
|---|---|
| `SHELLY_AUTH_KEY` | App Shelly → ajustes de usuario → "Authorization cloud key" |
| `SHELLY_SERVER_URI` | Aparece junto a la key (ej. `shelly-42-eu.shelly.cloud`) |
| `SHELLY_DEVICE_ID` | Ajustes del 1PM → Device Information → Device ID |
| `MELCLOUD_EMAIL` | Tu email de MELCloud |
| `MELCLOUD_PASSWORD` | Tu contraseña de MELCloud |

No hace falta guardar los DeviceID de los splits en ningún sitio: el script
los descubre solos en cada ejecución llamando a MELCloud.

(Opcional, solo para comprobar antes de fiarte del automatismo: ejecuta
`scripts/list_melcloud_devices.py` en tu propio ordenador, te pide el email
y contraseña por teclado y te imprime el nombre/ID de cada split. Nada de
esto sale de tu máquina.)

## 4. Primera prueba

Antes de dejarlo en piloto automático, ve a la pestaña *Actions* del repo,
elige el workflow "AC garrafa monitor" y dale a *Run workflow* (el trigger
`workflow_dispatch` está pensado justo para esto). Revisa el log: debería
leer el estado del Shelly sin errores. Repite provocando manualmente el
SW (con la boya) para ver un ciclo completo de apagado/reencendido antes de
confiar en él sin supervisión.

## 5. Ajustes que puedes tocar en `scripts/monitor.py`

- `STABLE_READS_NEEDED` (2): lecturas consecutivas iguales antes de actuar.
  Con cron cada 5 min, 2 lecturas = confirmación en ~5-10 min, suficiente
  para ignorar un toque accidental a la boya y lento respecto al tiempo
  real de llenado (horas).
- `FALLBACK_MINUTES` (10): tiempo de margen para que MELCloud confirme el
  apagado (vía caída de consumo) antes de cortar el relé como último
  recurso.
- `STANDBY_POWER_W` (15): consumo por debajo del cual se considera que los
  splits ya están apagados de verdad.

## Cómo funciona (resumen)

1. La boya activa el SW → confirmado tras 2 lecturas seguidas.
2. Se consulta a MELCloud qué splits están encendidos y se guarda esa foto.
3. Se manda `Power: false` por MELCloud a los que estaban encendidos.
4. Se comprueba el consumo del propio Shelly 1PM; si baja, confirmado, fin.
5. Si pasan `FALLBACK_MINUTES` sin que baje el consumo, se corta el relé
   como red de seguridad.
6. Al vaciarse la garrafa (SW confirmado abierto), si hubo que cortar el
   relé se reconecta primero (con margen para que el wifi de los splits
   arranque) y luego se manda `Power: true` solo a los splits que estaban
   encendidos en el paso 2.
7. Si no hay ningún cambio de estado durante 40 días, se hace un commit
   trivial para que GitHub no desactive el cron por inactividad.

## Notas

- La API de MELCloud usada aquí no es oficial (Mitsubishi no publica una
  API pública), así que puede cambiar sin aviso. Si algo deja de funcionar,
  lo primero es mirar el log del workflow.
