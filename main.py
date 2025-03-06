from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
import uvicorn
import os
import resend
from pathlib import Path
from jinja2 import Template
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging with more detailed settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Ensure logs go to stdout
    ]
)
logger = logging.getLogger(__name__)

# Add a test log message at startup
logger.info("=== Application starting up with enhanced logging ===")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

# Define the request model for the waitlist signup
class WaitlistSignup(BaseModel):
    email: EmailStr
    name: str

# Security key validation
def validate_security_key(security_key: str = Header(None, alias="X-Frontend-Key")):
    env_security_key = os.environ.get("FRONTEND_KEY")
    if not env_security_key:
        print("WARNING: FRONTEND_KEY not set in environment variables")
        logger.warning("FRONTEND_KEY not set in environment variables")
        # For development, allow requests without security key
        return "dev-mode"
    
    if not security_key:
        print(f"ERROR: Missing X-Frontend-Key header")
        logger.error(f"Missing X-Frontend-Key header")
        raise HTTPException(status_code=401, detail="Security key is required")
    
    print(f"SECURITY KEY: Received '{security_key}', Expected '{env_security_key}'")
    logger.info(f"Validating security key: '{security_key[:3]}...'")
    
    if security_key != env_security_key:
        print(f"ERROR: Invalid X-Frontend-Key header")
        logger.error(f"Invalid X-Frontend-Key header")
        raise HTTPException(status_code=403, detail="Invalid security key")
    
    return security_key

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI Backend!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "query": q}

@app.post("/items/")
def create_item(item: Item):
    return {"item": item}


# Set your Resend API key with a fallback
resend_api_key = os.environ.get("RESEND_API_KEY")
if not resend_api_key:
    resend_api_key = "re_hcWg7mPg_BaE6DGRwVuCiqD2sVLCdTJUq"  # Fallback key
    print(f"WARNING: Using fallback Resend API key: {resend_api_key[:5]}...{resend_api_key[-4:]}")
    logger.warning(f"Using fallback Resend API key: {resend_api_key[:5]}...{resend_api_key[-4:]}")

resend.api_key = resend_api_key
print(f"RESEND API KEY: Set to {resend_api_key[:5]}...{resend_api_key[-4:]}")
logger.info(f"Resend API key set to: {resend_api_key[:5]}...{resend_api_key[-4:]}")

# Load the email template
def get_email_template():
    template_path = Path("waitlist.html")
    if not template_path.exists():
        logger.error(f"Email template not found at path: {template_path.absolute()}")
        raise HTTPException(status_code=500, detail="Email template not found")
    logger.info(f"Email template found at: {template_path.absolute()}")
    return template_path.read_text()

@app.post("/waitlist/signup")
async def waitlist_signup(signup: WaitlistSignup, validated_key: str = Depends(validate_security_key)):
    try:
        print(f"SIGNUP REQUEST: {signup.email}, {signup.name}")
        logger.info(f"Received waitlist signup request for: {signup.email}, {signup.name}")
        
        # Security key is already validated by the dependency
        print("SECURITY KEY: Validated successfully")
        logger.info("Security key validated successfully")
        
        # Get the email template
        print("TEMPLATE: Fetching email template")
        logger.info("Fetching email template")
        template_content = get_email_template()
        
        # Extract first name from full name (for the template)
        first_name = signup.name.split()[0] if signup.name else ""
        print(f"FIRST NAME: {first_name}")
        logger.info(f"Extracted first name: {first_name}")
        
        # Get the server URL from environment or use a default
        server_url = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
        
        # Render the template with the subscriber's information
        print("TEMPLATE: Rendering email template")
        logger.info("Rendering email template")
        template = Template(template_content)
        html_content = template.render(
            subscriber={
                "first_name": first_name,
                "full_name": signup.name,
                "email": signup.email
            },
            server_url=server_url  # Add the server URL to the template context
        )
        print("TEMPLATE: Rendered successfully")
        logger.info("Template rendered successfully")
        
        # Send the email using Resend
        print(f"EMAIL: Sending to {signup.email}")
        logger.info(f"Sending email to: {signup.email}")
        
        # Check if Resend API key is set
        if not resend.api_key:
            print("ERROR: Resend API key is not set")
            logger.error("Resend API key is not set")
            raise ValueError("Resend API key is not configured")
            
        print(f"RESEND API KEY: {resend.api_key[:5]}...{resend.api_key[-4:] if resend.api_key else 'None'}")
        logger.info(f"Using Resend API key: {resend.api_key[:5]}...{resend.api_key[-4:] if resend.api_key else 'None'}")
        
        response = resend.Emails.send({
            "from": "Dojikets <noreply@dojikets.com>",
            "to": signup.email,
            "subject": "Welcome to the Dojikets Waitlist!",
            "html": html_content
        })
        
        print(f"EMAIL SENT: {response}")
        logger.info(f"Email sent successfully, response: {response}")
        
        return {
            "success": True,
            "message": f"Successfully added {signup.name} to waitlist",
            "email_id": response["id"] if "id" in response else None
        }
    except Exception as e:
        error_msg = f"Error in waitlist signup: {str(e)}"
        print(f"ERROR: {error_msg}")
        print(f"ERROR TYPE: {type(e).__name__}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# Add a route specifically for testing logging
@app.get("/test-log")
def test_log():
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    return {"message": "Logs generated, check your console"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    
    # Configure uvicorn logging to work with our logger
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info",
        access_log=True
    )