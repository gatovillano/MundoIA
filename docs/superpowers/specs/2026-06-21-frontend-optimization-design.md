# Especificación de Diseño: Optimización Integral del Frontend (Carga y FPS)

Fecha: 2026-06-21
Estado: Propuesto

## 1. Contexto y Problema

El frontend de MundoIA (construido sobre Next.js 16 y React 19) sufre de lentitud tanto en la carga inicial como durante el tiempo de ejecución (bajo framerate de simulación). Las causas específicas identificadas son:

1. **Bundle Inicial Masivo (Carga Inicial)**: La ruta principal del juego (`/game`) importa estáticamente todas las dependencias principales. Esto arrastra `three`, `@react-three/fiber`, `@react-three/drei`, `@react-three/postprocessing`, `postprocessing` y `d3` al chunk de carga inicial del navegador, provocando descargas de varios megabytes antes de mostrar la UI.
2. **Reflows de CSS por Cursor Animado (FPS)**: En `BackgroundEffects.tsx`, el evento del mouse actualiza las propiedades CSS `left` y `top` del blob de fondo mediante la API de animaciones web. Esto obliga al navegador a recalcular el layout de toda la página (*reflow*) en cada frame del movimiento del mouse.
3. **Destrucción y Recreación de Nodos en D3 (FPS)**: En `WorldViewport.tsx` (vista 2D isométrica), cada renderizado elimina todas las decoraciones, edificios y recursos (`cell.selectAll(...).remove()`) y las vuelve a insertar mediante operaciones DOM directas. Con un mapa mediano, esto genera miles de escrituras síncronas en el DOM del hilo principal.
4. **Cálculo de Texto Innecesario en Speech Bubbles (FPS)**: En `WorldViewport.tsx`, las burbujas de diálogo se vuelven a dividir en líneas y se redimensionan en el DOM en cada actualización de agentes o clima, consumiendo ciclos CPU de manera innecesaria.

## 2. Solución Propuesta

### 2.1. Carga Diferida (Lazy Loading) de Componentes Pesados

Modificar `web/frontend/src/app/game/page.tsx` para importar dinámicamente las tres vistas de renderizado pesado con `ssr: false`:

* `WorldViewport` (D3 Isométrico)
* `WorldViewport3D` (Three.js 3D)
* `NetworkView` (Grafo D3)

Esto separará automáticamente estas librerías masivas en chunks asíncronos independientes, disminuyendo drásticamente el peso de la primera carga.

### 2.2. Aceleración por Hardware (GPU) en BackgroundEffects

Modificar `web/frontend/src/components/BackgroundEffects.tsx` para:
* Reemplazar las propiedades animadas `left` y `top` por la transformación de coordenadas 3D `transform: translate3d(...)` que utiliza aceleración por GPU.
* Ajustar la estructura de clases Tailwind del blob fijándolo en `left-0 top-0` y aplicando la translación compensada (`calc(Xpx - 50%)`) de manera nativa.

### 2.3. Refactor del Renderizado de Celdas y Decoraciones en D3

Modificar `web/frontend/src/components/WorldViewport.tsx` para hacer las actualizaciones del mapa incrementales y eficientes:
* Eliminar el `.remove()` general de los elementos dinámicos por celda.
* **Terreno y Clima**: Verificar si el nodo ya existe antes de realizar la inserción.
* **Bosques**: Solo instanciar los árboles si el contenedor `.tree-unit` está vacío.
* **Recursos**: Adjuntar un atributo `data-type` para persistir el tipo del recurso actual. Si el recurso no ha cambiado, evitar recrear el SVG.
* **Edificios**: Usar el ciclo `.join()` de D3 sobre los datos del edificio o condicionar la renderización para no duplicar los bloques.
* **Burbujas de Diálogo**: Mover la lógica pesada de división de líneas y cálculo de cajas de texto (`rect` y `tspan`) al bloque `enter` de D3 (se ejecuta una única vez por burbuja). En el bloque de actualización (`update`), únicamente trasladar el grupo completo (`transform`) siguiendo las coordenadas del agente.

## 3. Plan de Pruebas y Validación

1. **Verificación de Compilación**:
   * Ejecutar la limpieza de caché de compilación si es necesario (limpiando el directorio `.next` con permisos gato si no hay problemas, o vía script alternativo).
   * Ejecutar `npm run build` en el directorio del frontend y comprobar que los bundles iniciales sean más pequeños (Next.js emite un reporte detallado con colores verde/amarillo indicando los tamaños).
2. **Pruebas de FPS y Rendimiento en Ejecución**:
   * Iniciar la aplicación y abrir la consola de desarrollo del navegador.
   * Realizar profiling del rendimiento (*Performance* tab) durante la simulación con el mapa 2D y el movimiento del cursor, confirmando que la métrica de FPS se mantenga estable a 60 FPS y no haya bloqueos en el hilo principal de renderizado.
