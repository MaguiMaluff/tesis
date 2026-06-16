# frontend/src/app/features/conversations

## Responsabilidad

Muestra las conversaciones monitoreadas y su detalle operativo.

## Archivos y función

- `conversations-module.ts`: módulo de carga diferida y rutas de la feature.
- `conversation.service.ts`: servicio base de la feature; hoy funciona como punto de extensión para acceso a datos de conversación.
- `list/`: listado principal de conversaciones.
- `detail/`: vista detallada de una conversación.

## Relación con el resto del proyecto

Consume `ApiService.getConversations()`, `ApiService.getConversation()` y `ApiService.getConversationEvents()`. Se apoya en la autenticación global y en el dashboard para navegar entre casos relacionados.