from .auth_controller import auth_bp
from .user_controller import user_bp
from .car_controller import car_bp
from .inspection_controller import inspection_bp
from .inquiry_controller import inquiry_bp
from .deal_controller import deal_bp

__all__ = ["auth_bp", "user_bp", "car_bp", "inspection_bp", "inquiry_bp", "deal_bp"]