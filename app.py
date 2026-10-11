import os
import sys
import uuid
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

# Local Module Imports
from config import Config
from models import db, Memory

# -----------------------------------------------------------------------------
# 1. Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger('MemoryVault')
logger.info("Initializing Memory Vault Application...")

# -----------------------------------------------------------------------------
# 2. Standard Flask Initialization (No Application Factory / No Blueprints)
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy with Flask App
db.init_app(app)

# Create Upload Directory locally if it doesn't exist (used when STORAGE_TYPE=local)
if app.config['STORAGE_TYPE'] == 'local' and not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logger.info(f"Created local upload directory at: {app.config['UPLOAD_FOLDER']}")

# -----------------------------------------------------------------------------
# 3. Simple Storage Abstraction Helper (Local Disk vs AWS S3 with IAM Role)
# -----------------------------------------------------------------------------
def save_image(file_storage):
    """
    Saves an uploaded image file depending on the STORAGE_TYPE environment setting.
    - If STORAGE_TYPE == 's3': Uploads to AWS S3 using boto3 with IAM Role credentials.
    - Otherwise ('local'): Saves to static/uploads/ and returns the relative path.
    """
    if not file_storage or file_storage.filename == '':
        raise ValueError("No file provided for upload.")

    # Generate a unique timestamped filename to prevent collisions
    filename = secure_filename(file_storage.filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"

    storage_type = app.config['STORAGE_TYPE']

    if storage_type == 's3':
        logger.info(f"Attempting image upload to AWS S3 Bucket: '{app.config['AWS_S3_BUCKET']}'")
        try:
            import boto3
            # Instantiate boto3 S3 client using EC2 IAM Role credentials automatically
            s3_client = boto3.client(
                's3',
                region_name=app.config['AWS_REGION']
            )

            # Upload stream directly to S3
            s3_client.upload_fileobj(
                file_storage,
                app.config['AWS_S3_BUCKET'],
                unique_filename,
                ExtraArgs={'ContentType': file_storage.content_type}
            )

            s3_url = f"https://{app.config['AWS_S3_BUCKET']}.s3.{app.config['AWS_REGION']}.amazonaws.com/{unique_filename}"
            logger.info(f"Image successfully uploaded to AWS S3: {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"S3 Upload failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to upload image to Amazon S3: {str(e)}")

    else:
        # Default: Local Disk Storage
        local_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file_storage.save(local_filepath)
        local_url = url_for('static', filename=f"uploads/{unique_filename}")
        logger.info(f"Image saved locally to disk: {local_filepath}")
        return local_url


# -----------------------------------------------------------------------------
# 4. View Routes & Handlers
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """Home Landing Page displaying welcome hero and 3 dashboard cards."""
    return render_template('index.html')


@app.route('/add', methods=['GET', 'POST'])
def add_memory():
    """Add Memory Page: Handles memory creation form and image upload."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        image_file = request.files.get('image')

        # Form Input Validation
        if not title or not description:
            flash("Title and Description are required fields.", "danger")
            return render_template('add_memory.html', title=title, description=description)

        if not image_file or image_file.filename == '':
            flash("Please select an image photograph to upload.", "danger")
            return render_template('add_memory.html', title=title, description=description)

        try:
            # 1. Save Image via Storage Helper
            image_url = save_image(image_file)

            # 2. Save Memory Record to MySQL Database
            new_memory = Memory(
                title=title,
                description=description,
                image_url=image_url
            )
            db.session.add(new_memory)
            db.session.commit()

            logger.info(f"Successfully created Memory record ID #{new_memory.id}: '{new_memory.title}'")
            flash("Your memory has been preserved successfully!", "success")
            return redirect(url_for('view_memories'))

        except SQLAlchemyError as db_err:
            db.session.rollback()
            logger.error(f"Database Error while saving memory: {str(db_err)}", exc_info=True)
            flash("Database Error: Could not save memory. Verify your MySQL database connection.", "danger")
            return render_template('add_memory.html', title=title, description=description)

        except Exception as err:
            logger.error(f"Unexpected Exception in add_memory: {str(err)}", exc_info=True)
            flash(f"Error processing request: {str(err)}", "danger")
            return render_template('add_memory.html', title=title, description=description)

    return render_template('add_memory.html')


@app.route('/memories')
def view_memories():
    """View Memories Page: Displays all memories sorted newest first."""
    try:
        memories = Memory.query.order_by(Memory.created_at.desc()).all()
        return render_template('view_memories.html', memories=memories)
    except SQLAlchemyError as db_err:
        logger.error(f"Database Query Error in view_memories: {str(db_err)}", exc_info=True)
        flash("Database Error: Unable to fetch memories. Check MySQL connection credentials.", "danger")
        return render_template('view_memories.html', memories=[])


@app.route('/search')
def search_memories():
    """Search Page: Filters memories by title or description keyword."""
    query = request.args.get('q', '').strip()
    memories = []

    if query:
        try:
            search_pattern = f"%{query}%"
            memories = Memory.query.filter(
                or_(
                    Memory.title.ilike(search_pattern),
                    Memory.description.ilike(search_pattern)
                )
            ).order_by(Memory.created_at.desc()).all()
            logger.info(f"Search query '{query}' matched {len(memories)} memory records.")
        except SQLAlchemyError as db_err:
            logger.error(f"Database Query Error during search: {str(db_err)}", exc_info=True)
            flash("Database Error: Could not perform search.", "danger")

    return render_template('search.html', memories=memories, query=query)


# -----------------------------------------------------------------------------
# 5. Database Initialization CLI & Helper (Separate from App Startup)
# -----------------------------------------------------------------------------
def init_db():
    """Explicit Helper function to initialize database tables."""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables initialized successfully.")
            return True
        except Exception as err:
            logger.error(f"Database table initialization failed: {err}", exc_info=True)
            return False

@app.cli.command('init-db')
def init_db_command():
    """Flask CLI command to initialize database tables: 'flask init-db'"""
    if init_db():
        print("Database tables created successfully.")
    else:
        print("Failed to initialize database tables. Check logs for details.")

if __name__ == '__main__':
    # If explicitly run with --init-db argument
    if len(sys.argv) > 1 and sys.argv[1] == '--init-db':
        init_db()
        sys.exit(0)

    logger.info("Starting Memory Vault Flask Server on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
