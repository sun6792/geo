"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.core.database import check_db_connection, async_session_factory

async def seed_defaults():
    """Auto-seed essential data for fresh databases (dev mode)."""
    from app.core.security import hash_password
    async with async_session_factory() as db:
        try:
            # Check if admin exists
            from sqlalchemy import select
            from app.models.account import User
            r = await db.execute(select(User).where(User.email == "admin@geoai.com").limit(1))
            if r.scalar_one_or_none():
                return  # Already seeded

            # Create platform customer
            from app.models.customer import Customer
            c = Customer(id="00000000-0000-0000-0000-000000000001", name="GEO AI Platform",
                         slug="geoai-platform", owner_email="admin@geoai.com",
                         subscription_tier="enterprise", max_users=999, max_kb_assets=9999)
            db.add(c)

            # Create admin user
            u = User(id="00000000-0000-0000-0000-000000000001",
                     customer_id="00000000-0000-0000-0000-000000000001",
                     email="admin@geoai.com", password_hash=hash_password("admin123"),
                     display_name="Platform Admin", is_super_admin=True, is_active=True)
            db.add(u)

            # Create demo customer
            c2 = Customer(id="00000000-0000-0000-0000-000000000002", name="Demo Enterprise",
                          slug="demo-enterprise", owner_email="demo@example.com",
                          subscription_tier="professional")
            db.add(c2)
            u2 = User(id="00000000-0000-0000-0000-000000000002",
                      customer_id="00000000-0000-0000-0000-000000000002",
                      email="demo@example.com", password_hash=hash_password("admin123"),
                      display_name="Demo Admin")
            db.add(u2)

            # Create default roles and permissions
            import uuid as _uuid
            perms_data = [
                ("customer:read","customer","read"), ("customer:create","customer","create"),
                ("customer:update","customer","update"), ("customer:delete","customer","delete"),
                ("account:read","account","read"), ("account:create","account","create"),
                ("account:update","account","update"), ("account:delete","account","delete"),
                ("kb:read","kb","read"), ("kb:create","kb","create"),
                ("kb:update","kb","update"), ("kb:delete","kb","delete"),
                ("content:read","content","read"), ("content:create","content","create"),
                ("content:update","content","update"), ("content:delete","content","delete"),
                ("review:read","review","read"), ("review:approve","review","approve"),
                ("review:comment","review","comment"),
                ("publish:read","publish","read"), ("publish:create","publish","create"),
                ("publish:update","publish","update"),
                ("system:read","system","read"), ("system:manage","system","manage"),
            ]
            from app.models.account import Permission, Role, RolePermission, UserRole
            perm_map = {}
            for code, res, act in perms_data:
                p = Permission(id=_uuid.uuid4(), code=code, resource=res, action=act)
                db.add(p)
                perm_map[code] = p

            # Create roles
            super_admin_role = Role(id=_uuid.uuid4(), name="超级管理员", code="super_admin", is_system=True, customer_id=None)
            admin_role = Role(id=_uuid.uuid4(), name="管理员", code="admin", is_system=True, customer_id=None)
            db.add(super_admin_role); db.add(admin_role)

            await db.flush()

            # Assign all permissions to super_admin
            for p in perm_map.values():
                db.add(RolePermission(role_id=super_admin_role.id, permission_id=p.id))

            # Assign admin role to admin user
            db.add(UserRole(user_id=u.id, role_id=super_admin_role.id))
            db.add(UserRole(user_id=u2.id, role_id=admin_role.id))

            await db.commit()
            print("SEED: Default data created (admin@geoai.com / admin123)")
        except Exception as e:
            await db.rollback()
            print(f"SEED: Already initialized or error: {e}")
from app.core.exceptions import AppException, app_exception_handler, generic_exception_handler
from app.core.logging_config import logger, setup_logging
from app.core.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────
    setup_logging(settings.LOG_LEVEL)
    logger.info("app.startup", version=settings.APP_VERSION, env="production" if not settings.DEBUG else "development")

    # Always attempt DB init (creates tables + seeds on first run)
    from app.core.database import init_db
    try:
        await init_db()
        logger.info("database.tables_created")
    except Exception as e:
        logger.warning("database.init_error", error=str(e))

    try:
        await seed_defaults()
    except Exception as e:
        logger.warning("database.seed_error", error=str(e))

    db_ok = await check_db_connection()
    if db_ok:
        logger.info("database.connected")
    else:
        logger.warning("database.unavailable")

    yield  # ── Application runs ──────────────────────────────

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Application factory: creates and configures the FastAPI instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Middleware
    setup_middleware(app)

    # Exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Routers ──────────────────────────────────────────────
    from app.api.public.health import router as health_router
    app.include_router(health_router)

    from app.api.public.client_review import router as client_review_router
    app.include_router(client_review_router, prefix="/api/public")

    from app.api.v1.router import api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
