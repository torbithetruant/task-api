from celery import Celery
import structlog

# Initialize Celery
# We use Redis as both the broker (for sending tasks) and backend (for results)
celery_app = Celery(
    "tasks", 
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

logger = structlog.get_logger()


@celery_app.task
def send_welcome_email(email: str, username: str):
    """
    Simulate sending a welcome email.
    In a real app, this would use SMTP or SendGrid.
    """
    logger.info("sending_welcome_email", email=email, username=username)
    
    # Simulate delay (e.g., connecting to email server)
    import time
    time.sleep(2) 
    
    logger.info("email_sent_successfully", email=email)
    return f"Email sent to {email}"