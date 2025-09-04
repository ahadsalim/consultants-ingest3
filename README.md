# Ingest - Legal Document Management System

A production-ready Django 5 application for managing legal documents with hierarchical structure, workflow management, and integration with core services.

## Features

- **Document Management**: Create, edit, and manage legal documents with hierarchical units
- **Workflow System**: Draft → Review → Approval workflow with role-based permissions
- **File Storage**: Secure file storage with MinIO and presigned URLs
- **Search & Categorization**: Vocabulary-based tagging and full-text search
- **API Integration**: RESTful API with JWT authentication and OpenAPI documentation
- **Vector Embeddings**: pgvector integration for semantic search (scaffolded)
- **Sync Bridge**: Automated synchronization with core services
- **Audit Trail**: Complete audit logging with django-simple-history

## Tech Stack

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL 16 with pgvector extension
- **Storage**: MinIO (S3-compatible)
- **Cache/Queue**: Redis + Celery
- **Authentication**: JWT tokens
- **Documentation**: OpenAPI/Swagger
- **Deployment**: Docker Compose

## Deploy (External MinIO)

### 1. Interactive Deployment

```bash
cd ingest
chmod +x deploy_ingest.sh
./deploy_ingest.sh
```

The deploy script will prompt for:
- **PostgreSQL**: Host, Port, Database, User, Password
- **Django**: Secret Key, Allowed Hosts
- **MinIO**: Endpoint URL, Access Key, Secret Key, Bucket Name

### 2. Manual Setup

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Start services (database + web only)
docker-compose -f docker-compose.ingest.yml up -d --build

# Run migrations
docker-compose -f docker-compose.ingest.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.ingest.yml exec web python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.ingest.yml exec web python manage.py collectstatic --noinput
```

### 3. Access the Application

- **Admin Interface**: http://localhost:8001/admin/
- **API Documentation**: http://localhost:8001/api/schema/swagger-ui/
- **Health Check**: http://localhost:8001/api/health/

### 4. Process Sync Jobs

```bash
# Process pending sync jobs manually
docker-compose -f docker-compose.ingest.yml exec web python manage.py process_syncjobs

# Dry run to see what would be processed
docker-compose -f docker-compose.ingest.yml exec web python manage.py process_syncjobs --dry-run
```

## User Roles

### Operator
- Create and edit own documents/QA entries
- Submit content for review
- View masterdata

### Reviewer
- All Operator permissions
- Approve/reject content from any user
- Manage masterdata

### Admin
- All permissions
- System administration
- Edit approved content

## API Usage

### Authentication

```bash
# Get JWT token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/documents/
```

### Key Endpoints

- `GET /api/health/` - Health check
- `GET /api/documents/` - List documents
- `POST /api/documents/` - Create document
- `GET /api/documents/{id}/units/` - Get document units
- `POST /api/presign/` - Generate presigned URLs
- `GET /api/sync/jobs/` - View sync jobs

## File Upload Process

1. **Get presigned URL**:
```bash
curl -X POST http://localhost:8000/api/presign/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "document.pdf", "content_type": "application/pdf"}'
```

2. **Upload file to MinIO**:
```bash
curl -X PUT "PRESIGNED_UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @document.pdf
```

3. **Create FileAsset record** via API

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Running Tests

```bash
# Run all tests
docker-compose -f docker-compose.ingest.yml exec web pytest

# Run with coverage
docker-compose -f docker-compose.ingest.yml exec web pytest --cov=ingest

# Run specific test file
docker-compose -f docker-compose.ingest.yml exec web pytest tests/test_models.py
```

### Management Commands

```bash
# Initialize user roles and permissions
python manage.py init_roles

# Initialize pgvector extension
python manage.py init_pgvector

# Create superuser if none exists
python manage.py create_superuser_if_absent

# Create sample data
python manage.py seed_data
```

## Data Model

### Core Entities

- **Jurisdiction**: Legal jurisdictions (e.g., Iran, provinces)
- **IssuingAuthority**: Organizations that issue documents
- **Vocabulary/VocabularyTerm**: Categorization system
- **LegalDocument**: Main document entity with workflow
- **LegalUnit**: Hierarchical document structure (MPTT)
- **QAEntry**: Question/Answer pairs
- **FileAsset**: File attachments
- **SyncJob**: Synchronization tasks

### Workflow States

- **Draft**: Editable by creator
- **Under Review**: Submitted for approval
- **Approved**: Read-only, synced to core
- **Rejected**: Returned to draft

## Integration

### Core Service Sync

When documents/QA entries are approved, they're automatically queued for sync to the core service:

```json
{
  "type": "legal_document",
  "id": "uuid",
  "title": "Document Title",
  "jurisdiction": {"id": "uuid", "name": "Iran", "code": "IR"},
  "authority": {"id": "uuid", "name": "Majles", "code": "MAJLES"},
  "units": [...],
  "files": [...]
}
```

### Vector Embeddings

The system is scaffolded for vector embeddings using pgvector:

```bash
# Generate embeddings for approved content
docker-compose -f docker-compose.ingest.yml exec web python manage.py shell
>>> from ingest.apps.embeddings.tasks import batch_generate_embeddings
>>> batch_generate_embeddings.delay()
```

## Configuration

### Environment Variables

See `.env.example` for all configuration options.

Key settings:
- `CORE_BASE_URL`: Core service endpoint
- `CORE_TOKEN`: Authentication token for core service
- `MINIO_*`: MinIO/S3 configuration
- `EMBEDDING_DIMENSION`: Vector dimension (default: 384)

### Ports (configurable)

- Web: 8000
- PostgreSQL: 5432
- Redis: 6379
- MinIO: 9000 (API), 9001 (Console)

## Production Deployment

1. **Security**: Change all default passwords and tokens
2. **SSL**: Enable HTTPS and update CORS settings
3. **Monitoring**: Add logging and monitoring solutions
4. **Backup**: Configure database and file storage backups
5. **Scaling**: Use external PostgreSQL/Redis for production

## Troubleshooting

### Common Issues

1. **Database connection failed**: Check PostgreSQL is running and credentials are correct
2. **MinIO access denied**: Verify MinIO credentials and bucket permissions
3. **Celery tasks not running**: Ensure Redis is accessible and worker is running
4. **Import errors**: Run migrations and ensure all dependencies are installed

### Logs

```bash
# View application logs
docker-compose -f docker-compose.ingest.yml logs web

# View worker logs
docker-compose -f docker-compose.ingest.yml logs worker

# View database logs
docker-compose -f docker-compose.ingest.yml logs db
```

## License

This project is proprietary software for legal document management.

## Support

For technical support, please contact the development team.
