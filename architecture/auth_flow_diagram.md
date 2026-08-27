# Authentication & JWT Lifecycle Architecture

This sequence diagram illustrates the stateless JWT Bearer token authentication lifecycle, token expiration checks, and upstream delegation to downstream agent and MCP microservices.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client UI
    participant Frontend as AI-PLT-UI (React SPA)
    participant Backend as AI-PLT-BE (FastAPI)
    participant DB as SQLite / Cloud SQL (Users & RBAC)
    participant Upstream as Agent Service / MCP Servers

    %% Login Flow
    User->>Frontend: Enters Email & Password
    Frontend->>Backend: POST /api/v1/auth/login
    Backend->>DB: Query User & verify bcrypt password
    DB-->>Backend: User Record (role: developer, credits: 20)
    Backend->>Backend: Generate JWT with exp (1h) & claims
    Backend-->>Frontend: 200 OK { access_token, user }
    Note over Frontend: Stores access_token in memory / localStorage

    %% Authenticated Chat Call
    User->>Frontend: Sends Chat Prompt
    Frontend->>Backend: GET /api/v1/chat/stream (Header: Authorization: Bearer <token>)
    
    rect rgb(235, 248, 255)
    Note over Backend: 1. Verify HMAC-SHA256 signature<br/>2. Verify token is not expired (exp > now)<br/>3. Single SQL JOIN to fetch User + Role + Permissions
    end

    alt Invalid Token / Expired
        Backend-->>Frontend: 401 Unauthorized
        Frontend->>User: Redirect to Login Screen
    else Valid Token & Has Credits
        Backend->>Upstream: Forward Prompt + Authorization: Bearer <token>
        Upstream-->>Backend: Stream LLM Tokens / Execute Authorized MCPs
        Backend-->>Frontend: Stream SSE Tokens
        Backend->>DB: Deduct 1 Credit & Increment Tokens Used
    end
```
