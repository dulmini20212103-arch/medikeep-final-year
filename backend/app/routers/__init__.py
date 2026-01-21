#router package initializer
#controls how API route modules are exposed and imported.
#Each imported router is renamed
from .auth import router as auth_router
from .users import router as users_router

#defines what is publicly exposed when someone imports this package
__all__ = ["auth_router", "users_router"]