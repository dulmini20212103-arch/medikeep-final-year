import time
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.security import rate_limiter, get_client_ip

#Handles rate limiting + security headers.
class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for rate limiting and basic protection."""
    
    async def dispatch(self, request: Request, call_next):
        # Rate limiting
        #extracts the IP address of the client making the request
        client_ip = get_client_ip(request)
        
        # Different limits for different endpoints
        if request.url.path.startswith('/documents/upload'):
            max_requests = 10  # 10 uploads per hour
            #widow is the time period in seconds
            window = 3600
        elif request.url.path.startswith('/auth/'):
            max_requests = 5   # 5 auth attempts per hour
            window = 3600
        else:
            max_requests = 1000  # 1000 general requests per hour
            window = 3600
        
        #checks if this IP has exceeded the allowed requests.
        if not rate_limiter.is_allowed(client_ip, max_requests, window):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Add security headers
        #Calls the next middleware (call_next) and waits for the response.
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"  #Prevents browsers from interpreting files as a different MIME type.
        response.headers["X-Frame-Options"] = "DENY" #Prevents clickjacking by disallowing embedding in iframes.
        response.headers["X-XSS-Protection"] = "1; mode=block" #Enables cross-site scripting protection.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains" #Forces HTTPS for a year.
        response.headers["Content-Security-Policy"] = "default-src 'self'"  #Restricts content sources to only the same origin.
        
        return response

#Handles CSRF protection for sensitive requests.
class CSRFMiddleware(BaseHTTPMiddleware):
    """Basic CSRF protection for state-changing operations."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)
        
        # Skip for auth endpoints (handled by authentication)
        if request.url.path.startswith('/auth/'):
            return await call_next(request)
        
        # Check for presence of authorization header for state-changing requests
        #basic CSRF protection mechanism, if a request doesn’t have the correct auth token, it likely didn’t originate from the app.
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF protection: Authorization header required"}
            )
        
        #If the check passes, the request is sent to the next middleware
        return await call_next(request)
    
    #SecurityMiddleware and CSRFMiddleware,these classes work together to make the FastAPI app more secure against abuse and attacks.