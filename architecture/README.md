# AI Platform Architecture & Schemas

This directory contains architectural and database entity-relationship (ER) diagrams documenting the design of the AI Platform.

## Available Architecture Diagrams

1. **[database_er_diagram.md](./database_er_diagram.md)** (Raw: [database_schema.mmd](./database_schema.mmd))
   * Entity-Relationship diagram covering User Management, Role-Based Access Control (RBAC), Permissions, and Chat Threads.
2. **[auth_flow_diagram.md](./auth_flow_diagram.md)**
   * Sequence diagram of JWT authentication, validation, token expiration, and upstream delegation.
3. **[mcp_rbac_flow_diagram.md](./mcp_rbac_flow_diagram.md)**
   * Flowchart detailing the two-gate MCP tool filtering and runtime execution firewall.
      