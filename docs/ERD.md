# Entity Relationship Diagram

```mermaid
erDiagram
    %% User Management
    User ||--o{ LegalDocument : creates
    User ||--o{ QAEntry : creates
    User ||--o{ FileAsset : uploads
    User ||--o{ LoginEvent : generates
    
    %% Masterdata
    Jurisdiction ||--o{ IssuingAuthority : contains
    Jurisdiction ||--o{ LegalDocument : governs
    IssuingAuthority ||--o{ LegalDocument : issues
    
    Vocabulary ||--o{ VocabularyTerm : contains
    VocabularyTerm }o--o{ LegalDocument : categorizes
    VocabularyTerm }o--o{ QAEntry : tags
    
    %% Documents
    LegalDocument ||--o{ LegalUnit : contains
    LegalDocument ||--o{ FileAsset : attachments
    LegalDocument ||--o{ QAEntry : source
    LegalDocument ||--o{ DocumentRelation : from_document
    LegalDocument ||--o{ DocumentRelation : to_document
    
    LegalUnit ||--o{ LegalUnit : parent_child
    LegalUnit ||--o{ FileAsset : attachments
    LegalUnit ||--o{ QAEntry : source
    
    %% Sync & Embeddings
    LegalDocument ||--o{ SyncJob : triggers
    QAEntry ||--o{ SyncJob : triggers
    LegalUnit ||--o{ Embedding : generates
    LegalDocument ||--o{ Embedding : generates
    QAEntry ||--o{ Embedding : generates
    
    %% Entity Definitions
    User {
        int id PK
        string username
        string email
        string first_name
        string last_name
        boolean is_active
        datetime date_joined
    }
    
    LoginEvent {
        uuid id PK
        int user_id FK
        string ip_address
        text user_agent
        datetime timestamp
        boolean success
    }
    
    Jurisdiction {
        uuid id PK
        string name
        string code UK
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    IssuingAuthority {
        uuid id PK
        string name
        string code UK
        uuid jurisdiction_id FK
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    Vocabulary {
        uuid id PK
        string name
        string code UK
        text description
        datetime created_at
        datetime updated_at
    }
    
    VocabularyTerm {
        uuid id PK
        uuid vocabulary_id FK
        string term
        string code
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    LegalDocument {
        uuid id PK
        string title
        string reference_no
        string doc_type
        uuid jurisdiction_id FK
        uuid authority_id FK
        date enactment_date
        date effective_date
        date expiry_date
        string status
        int created_by FK
        int reviewed_by FK
        int approved_by FK
        datetime created_at
        datetime updated_at
    }
    
    DocumentRelation {
        uuid id PK
        uuid from_document_id FK
        uuid to_document_id FK
        string relation_type
        datetime created_at
        datetime updated_at
    }
    
    LegalUnit {
        uuid id PK
        uuid document_id FK
        uuid parent_id FK
        string unit_type
        string label
        string number
        int order_index
        string path_label
        text content
        int tree_id
        int lft
        int rght
        int level
        datetime created_at
        datetime updated_at
    }
    
    FileAsset {
        uuid id PK
        uuid document_id FK
        uuid legal_unit_id FK
        string bucket
        string object_key
        string original_filename
        string content_type
        bigint size_bytes
        string sha256
        int uploaded_by FK
        datetime created_at
        datetime updated_at
    }
    
    QAEntry {
        uuid id PK
        text question
        text answer
        uuid source_document_id FK
        uuid source_unit_id FK
        string status
        int created_by FK
        int reviewed_by FK
        int approved_by FK
        datetime created_at
        datetime updated_at
    }
    
    SyncJob {
        uuid id PK
        string job_type
        uuid target_id
        json payload_preview
        string status
        text last_error
        int retry_count
        int max_retries
        datetime next_retry_at
        datetime completed_at
        datetime created_at
        datetime updated_at
    }
    
    Embedding {
        uuid id PK
        int content_type_id FK
        uuid object_id
        string model_name
        vector vector
        text text_content
        datetime created_at
        datetime updated_at
    }
```

## Key Relationships

### Masterdata Hierarchy
- **Jurisdiction** → **IssuingAuthority** → **LegalDocument**
- **Vocabulary** → **VocabularyTerm** → **Documents/QA** (M2M)

### Document Structure
- **LegalDocument** contains multiple **LegalUnit** (hierarchical via MPTT)
- Both can have **FileAsset** attachments
- **DocumentRelation** links documents (amends, repeals, etc.)

### Workflow
- Users create content in **Draft** status
- **Reviewers** can approve → triggers **SyncJob**
- **SyncJob** sends data to core service

### Search & Analytics
- **Embedding** stores vectors for semantic search
- Links to any content via Generic Foreign Key

## Indexes

### Performance Indexes
- `LegalDocument`: `(status, created_at)`, `(jurisdiction, authority)`
- `LegalUnit`: `(document, tree_id, lft)`, `(unit_type)`
- `FileAsset`: `(document)`, `(legal_unit)`, `(content_type)`
- `QAEntry`: `(status, created_at)`, `(source_document)`
- `SyncJob`: `(status, created_at)`, `(job_type)`
- `Embedding`: `(content_type, object_id)`, `(model_name)`

### Unique Constraints
- `Jurisdiction.code`
- `IssuingAuthority.code`
- `Vocabulary.code`
- `VocabularyTerm.(vocabulary, code)`
- `DocumentRelation.(from_document, to_document, relation_type)`
