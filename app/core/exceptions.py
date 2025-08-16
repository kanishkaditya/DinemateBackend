from fastapi import HTTPException, status


class DineMateException(Exception):
    """Base exception class for DineMate"""
    pass


class AuthenticationError(DineMateException):
    """Authentication related errors"""
    pass


class AuthorizationError(DineMateException):
    """Authorization related errors"""
    pass


class NotFoundError(DineMateException):
    """Resource not found errors"""
    pass


class ValidationError(DineMateException):
    """Validation related errors"""
    pass


class ExternalServiceError(DineMateException):
    """External service (like Foursquare API) errors"""
    pass


# HTTP Exception helpers
class HTTPExceptions:
    @staticmethod
    def unauthorized(detail: str = "Could not validate credentials"):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    @staticmethod
    def forbidden(detail: str = "Not enough permissions"):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )
    
    @staticmethod
    def not_found(detail: str = "Resource not found"):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
    
    @staticmethod
    def bad_request(detail: str = "Bad request"):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    
    @staticmethod
    def conflict(detail: str = "Resource already exists"):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )
    
    @staticmethod
    def internal_server_error(detail: str = "Internal server error"):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )