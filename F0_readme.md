# 🚀 F0: El Super-Boilerplate para tu Próximo SaaS (Versión a Prueba de Dummies)

Hola. Si estás aquí, quieres construir una aplicación web (SaaS) y quieres hacerlo rápido, pero sin hacer "código espagueti". Has llegado al lugar correcto.

Piensa en **F0** como los "cimientos preconstruidos" de una mansión. No tienes que preocuparte por instalar la plomería o el cableado eléctrico; solo llegas, eliges el color de las paredes y empiezas a construir tus habitaciones.

---

## 🏗️ ¿Qué trae ya armado tu Mansión de Código?

1. **La Puerta de Seguridad (Autenticación y Roles):** 
   Ya nadie puede entrar a tu aplicación sin permiso. Si alguien se registra, su contraseña se guarda de forma secreta (hasheada). Si inician sesión, se les da un "Ticket" (Token JWT) para que sigan usando la app.
   *Si no tienes pase VIP (como Rol de ADMIN), no pasas.*

2. **La Caja Fuerte (Base de Datos):**
   Las configuraciones están listas para hablar con PostgreSQL. Todo funciona mediante **Modelos** abstractos, lo que significa que en vez de escribir código difícil de SQL, manipulas datos comunes como si fueran objetos de Python.

3. **La Memoria Fotográfica (Trazabilidad):**
   Agregamos una regla de oro llamada `AuditableBase`. Todo lo que guardes a futuro tendrá una fecha de registro (`created_at`) y una fecha de última actualización (`updated_at`). ¡Incluso tiene la **Papelera de Reciclaje** (`is_deleted`)! Nada se borra permanentemente si cometes un error. 

4. **El Perímetro Protegido (CORS):**
   Nadie externo a tu página de Frontend autorizada podrá "robar" datos a tu servidor. Esto se controla con algo llamado CORS (y lo ajustas fácilmente en tu archivo de configuraciones secreto `.env`).

---

## 🚦 Las Instrucciones Resumidas para Principiantes

1. **Consigue tu `.env`:** 
   Ese archivo oculto es donde pones tus secretos. Haz una copia del que se llama `.env.example`, nómbralo solamente `.env` y ahí vas a definir que quieres que el token de inicio de sesión dure días o minutos, o dónde se ubica tu Base de Datos externa (Supabase, por ejemplo).

2. **Carga los programas de construcción (`uv`):**
   No más comandos lentos de internet. Usa `uv sync` en tu terminal para instalar la magia requerida por Python rapidísmo.

3. **Construye las tablas (Alembic):**
   Son como los arquitectos creando las carpetas. Ejecutas `alembic upgrade head`, y magia: la tabla de Usuarios está oficialmente creada en la base de Datos.

4. **Arranca tu Proyecto:**
   Corre en tu terminal `uvicorn main:app --reload`. Si abres tu navegador en `http://localhost:8000/docs`, verás un panel increíble y automático en donde vas a poder probar cada paso de login.

---

## 🍕 ¿Qué hay en las Carpetas? (Explicado de manera simple)
- `/api`: La recepcionista. Toma las peticiones web y da respuestas genéricas.
- `/services`: El gerente. Decide las reglas del negocio, revisa si un usuario no está baneado antes de dejarle hacer algo.
- `/repositories`: El operario del almacén. Es el único que mueve las cajas (SQL) de un lado a otro.
- `/models`: Los moldes con forma exacta para cada dato.
- `/core`: La caja de herramientas. Cosas pesadas de conexión y configuraciones.

¡Eso es! Tu base de operaciones está lista para que escribas la idea de software de tus sueños.
