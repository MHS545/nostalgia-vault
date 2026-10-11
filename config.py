import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if available (primarily for local development)
load_dotenv()

logger = logging.getLogger('MemoryVaultConfig')

def get_database_credentials():
    """
    Retrieves database credentials.
    In production (default), fetches credentials dynamically from AWS Secrets Manager using the EC2 IAM Role.
    Set USE_SECRETS_MANAGER=false in local .env to bypass Secrets Manager during local testing.
    """
    use_secrets_manager = os.environ.get('USE_SECRETS_MANAGER', 'true').lower() in ('true', '1', 'yes')
    secret_name = os.environ.get('AWS_SECRET_NAME', 'memory-vault/database')
    region_name = os.environ.get('AWS_REGION', 'us-east-1')

    if use_secrets_manager:
        try:
            import boto3
            # Instantiate boto3 client WITHOUT explicit access keys to automatically use EC2 IAM Role
            client = boto3.client('secretsmanager', region_name=region_name)
            response = client.get_secret_value(SecretId=secret_name)
            
            secret_string = response.get('SecretString')
            if secret_string:
                secret_dict = json.loads(secret_string)
                logger.info(f"Successfully retrieved database credentials from AWS Secrets Manager ({secret_name}).")
                return {
                    'DB_HOST': secret_dict.get('DB_HOST') or secret_dict.get('host') or os.environ.get('DB_HOST', 'localhost'),
                    'DB_PORT': str(secret_dict.get('DB_PORT') or secret_dict.get('port') or os.environ.get('DB_PORT', '3306')),
                    'DB_NAME': secret_dict.get('DB_NAME') or secret_dict.get('dbname') or secret_dict.get('db_name') or os.environ.get('DB_NAME', 'memory_vault'),
                    'DB_USER': secret_dict.get('DB_USER') or secret_dict.get('username') or secret_dict.get('user') or os.environ.get('DB_USER', 'root'),
                    'DB_PASSWORD': secret_dict.get('DB_PASSWORD') or secret_dict.get('password') or os.environ.get('DB_PASSWORD', 'password'),
                }
        except Exception as e:
            logger.warning(f"AWS Secrets Manager lookup for '{secret_name}' failed or not available ({e}). Falling back to local environment variables.")

    # Fallback to local environment variables (.env)
    return {
        'DB_HOST': os.environ.get('DB_HOST', 'localhost'),
        'DB_PORT': os.environ.get('DB_PORT', '3306'),
        'DB_NAME': os.environ.get('DB_NAME', 'memory_vault'),
        'DB_USER': os.environ.get('DB_USER', 'root'),
        'DB_PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
    }

class Config:
    """
    Production Application Configuration Class.
    Integrates AWS Secrets Manager, Amazon S3 (IAM Role based), and MySQL RDS.
    """

    # Flask Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Retrieve Database Credentials from AWS Secrets Manager (Default) or Local .env
    _db_creds = get_database_credentials()
    DB_USER = _db_creds['DB_USER']
    DB_PASSWORD = _db_creds['DB_PASSWORD']
    DB_HOST = _db_creds['DB_HOST']
    DB_PORT = _db_creds['DB_PORT']
    DB_NAME = _db_creds['DB_NAME']

    # Construct SQLAlchemy Database URI for MySQL (RDS or local)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Upload & Storage Settings ('s3' by default for AWS production deployment, or 'local')
    STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 's3').lower()
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload limit

    # Amazon S3 Configuration (Uses EC2 IAM Role)
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET', 'waniya-memory-vault-images')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
