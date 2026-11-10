# Conexión real de solo lectura a tus servicios AWS

## Qué cambia

La aplicación continúa en Docker/SQLite. El importador corre desde Python en tu computadora, utiliza un perfil AWS local y consulta metadatos de recursos existentes. No requiere terraform apply ni crea Lambda, ECR, API Gateway, DynamoDB o CloudWatch adicionales.

El conector está implementado y probado con respuestas simuladas. La conexión con tu cuenta todavía requiere ejecutarlo con tu perfil: no se ha comprobado una conexión real ni se ha descubierto tu inventario desde este entorno.

## Servicios y alcance

| Servicio | Consulta | Alcance |
| --- | --- | --- |
| CloudFront | ListDistributions | Distribuciones de la cuenta; global |
| Lightsail | GetInstances | Instancias en la región indicada |
| DynamoDB | ListTables | Nombres de tablas de la región indicada; sin leer registros |
| S3, opcional | ListBuckets | Nombres de buckets de la cuenta; sin objetos ni archivos |

El importador no analiza permisos de bucket, no escanea vulnerabilidades, no comprueba salud de aplicaciones, no lee tablas, archivos, contraseñas ni logs, y no modifica recursos AWS. Un recurso descubierto es evidencia de que la API devolvió ese recurso, no de que sea seguro o esté sano.

## Costos

No se añade infraestructura facturable por ejecutar este importador. Sin embargo, solo lectura no significa que toda API AWS sea gratis: revisa la tarifa de las operaciones utilizadas y de cualquier servicio de auditoría que ya tengas configurado. S3 es opcional por ese motivo. Se hace una ejecución manual, con límite de 50 recursos por servicio (máximo configurable: 100), sin programación ni polling. El límite es de recursos entregados; un listado puede devolver más metadatos en su página y un SDK puede reintentar llamadas.

Desplegar el Terraform es una opción diferente: crearía ECR, Lambda, API Gateway, DynamoDB con recuperación a un punto en el tiempo, y logs/alarma CloudWatch, que pueden generar cargos por almacenamiento, solicitudes, ejecución, backups y monitoreo. El importador local no necesita ese despliegue.

## Autenticación

Utiliza un perfil de AWS CLI ya configurado en TU computadora, preferiblemente con credenciales temporales. Las credenciales se obtienen del perfil local mediante boto3 y nunca se agregan al repositorio ni se montan en Docker. No me envíes claves, tokens ni archivos de credenciales.

Un rol/perfil dedicado debe tener solo los permisos de policies/inventory-readonly.json. Las operaciones de listado incluidas usan Resource "*" porque listan colecciones de la cuenta. Para incluir S3, agrega también policies/inventory-s3-optional.json. Estas políticas no conceden lectura del contenido de buckets o tablas ni permisos de escritura. Las políticas son documentación para configurar tu rol; el proyecto no las aplica automáticamente.

## Probar primero sin importar

Desde la carpeta del proyecto en PowerShell:

```powershell
python -m pip install -r requirements-aws.txt
python scripts/import_aws.py --profile TU_PERFIL --region TU_REGION --limit 10
```

Sustituye ambos valores por el perfil local y la región de tus recursos. CloudFront es global; Lightsail y DynamoDB solo consultan esa región. Para otra región, ejecuta nuevamente. La vista previa consulta AWS de verdad pero no escribe activos en la API local. Sí crea una clave privada local de pseudonimización dentro de data/.

Si usas autenticación SSO, inicia previamente la sesión del perfil con tu mecanismo habitual. Si no tienes un perfil de lectura, configura uno antes de ejecutar; no uses credenciales de root.

## Importar al inventario local

Inicia la nueva versión:

```powershell
docker compose up --build
```

En otra terminal de tu computadora, situada en la carpeta del proyecto:

```powershell
python scripts/import_aws.py --profile TU_PERFIL --region TU_REGION --limit 10 --import-local
Invoke-RestMethod http://localhost:8080/assets | ConvertTo-Json -Depth 5
```

Para incluir S3, después de revisar sus permisos y costos:

```powershell
python scripts/import_aws.py --profile TU_PERFIL --region TU_REGION --services cloudfront lightsail dynamodb s3 --limit 10 --import-local
```

Los registros importados contienen alias como cloudfront-<fingerprint>, el tipo de servicio y la etiqueta Personal AWS inventory. No se almacenan nombres AWS, ARNs, números de cuenta, IDs de distribución, dominios ni IPs. Repetir con el mismo perfil y clave omite referencias existentes. No sincroniza eliminaciones ni actualiza estados del recurso; es una importación puntual del inventario, no monitoreo continuo. Si la importación local falla a mitad, algunos registros pueden haberse guardado: repetir omite los que ya existen.

## Privacidad

Los alias se calculan con HMAC-SHA256, usando una clave local en data/inventory-alias.key. El perfil también participa en el cálculo. Sin esa clave no se puede recalcular fácilmente el alias a partir de un nombre candidato; no equivale a anonimización absoluta. Cambiar perfil o perder la clave produce nuevos alias y puede crear duplicados.

La clave, la base SQLite y cualquier exportación privada deben permanecer fuera de Git. Si respaldas la base, respalda también la clave de forma privada. No hay un archivo de correspondencia entre alias y nombres reales en esta versión.

Solo publica capturas de las respuestas saneadas del inventario. La consola AWS, trazas de SDK, terminales de autenticación y registros manuales pueden contener otros identificadores. El sitio público registrado en la prueba manual anterior sigue siendo un registro independiente: no se borra ni se convierte en alias automáticamente.

## Qué demostrar en GitHub

Una vez ejecutado correctamente con tu cuenta, puedes documentar que integraste un inventario local con metadatos de servicios AWS existentes mediante SDK y permisos de lectura. Antes de publicarlo, confirma los resultados reales y toma una captura de /assets con alias. No describas una conexión exitosa ni cantidades de recursos hasta haberla verificado.

## Fuentes de precios

- https://aws.amazon.com/s3/pricing/
- https://aws.amazon.com/lambda/pricing/
- https://aws.amazon.com/api-gateway/pricing/
- https://aws.amazon.com/ecr/pricing/
- https://aws.amazon.com/dynamodb/pricing/
- https://aws.amazon.com/cloudwatch/pricing/
