# API Endpoints Documentation

## Authentication (`/auth`)

### POST `/auth/login`
- **Description**: Login and get access token
- **Body**: `{ "username": "string", "password": "string" }`
- **Response**: `{ "access_token": "string", "token_type": "bearer" }`
- **Auth**: None

### GET `/auth/me`
- **Description**: Get current user info
- **Response**: `{ "username": "string", "email": "string", "role": "admin", ... }`
- **Auth**: Required (Bearer token)

### POST `/auth/change-password`
- **Description**: Change current user's password
- **Body**: `{ "current_password": "string", "new_password": "string" }`
- **Response**: `{ "message": "Password updated" }`
- **Auth**: Required (Bearer token)

---

## Users (`/users`)

### GET `/users`
- **Description**: List all users (without password_hash and role)
- **Response**: `[{ "username": "string", "email": "string", ... }]`
- **Auth**: Admin only

### POST `/users`
- **Description**: Create a new user
- **Body**: `{ "username": "string", "email": "string", "temp_password": "string (optional)" }`
- **Response**: `{ "message": "User created", "temp_password": "string" }`
- **Auth**: Admin only

### GET `/users/{username}`
- **Description**: Get user details
- **Response**: `{ "username": "string", "email": "string", ... }`
- **Auth**: Admin only

### PUT `/users/{username}`
- **Description**: Update user details
- **Body**: `{ "username": "string", "email": "string", "temp_password": "string (optional)" }`
- **Response**: Updated user object
- **Auth**: Admin only

### DELETE `/users/{username}`
- **Description**: Delete a user (cannot delete admin)
- **Response**: `{ "message": "User deleted" }`
- **Auth**: Admin only
- **Note**: Also deletes all project memberships

---

## Projects (`/projects`)

### GET `/projects`
- **Description**: List projects (admin sees all, others see only their projects)
- **Response**: `[{ "project_id": "string", "name": "string", ... }]`
- **Auth**: Required (Bearer token)

### POST `/projects`
- **Description**: Create a new project
- **Body**: `{ "name": "string", "description": "string (optional)" }`
- **Response**: Created project object
- **Auth**: Admin only
- **Note**: Creator is automatically added as manager

### GET `/projects/{project_id}`
- **Description**: Get project details
- **Response**: Project object
- **Auth**: Required (must be member or admin)

### PUT `/projects/{project_id}`
- **Description**: Update project details
- **Body**: `{ "name": "string", "description": "string (optional)" }`
- **Response**: Updated project object
- **Auth**: Admin or project manager

### DELETE `/projects/{project_id}`
- **Description**: Delete a project
- **Response**: `{ "message": "Project deleted" }`
- **Auth**: Admin only
- **Note**: Also deletes all project members

---

## Project Members (`/projects/{project_id}/members`)

### GET `/projects/{project_id}/members`
- **Description**: List all members of a project
- **Response**: `[{ "project_id": "string", "username": "string", "role": "manager|engineer|viewer", ... }]`
- **Auth**: Required (must be member or admin)

### POST `/projects/{project_id}/members`
- **Description**: Add or update a member in a project
- **Body**: `{ "username": "string", "role": "manager|engineer|viewer" }`
- **Response**: `{ "message": "Member added/updated", "upserted": boolean }`
- **Auth**: Admin or project manager

### PUT `/projects/{project_id}/members/{username}`
- **Description**: Update a member's role in a project
- **Body**: `{ "username": "string", "role": "manager|engineer|viewer" }`
- **Response**: `{ "message": "Member role updated" }`
- **Auth**: Admin or project manager

### DELETE `/projects/{project_id}/members/{username}`
- **Description**: Remove a member from a project
- **Response**: `{ "message": "Member removed" }`
- **Auth**: Admin or project manager

---

## AI Test (`/ai/test`)

### GET `/ai/test`
- **Description**: Test Ollama connection
- **Response**: `{ "model": "string", "reply": "string" }`
- **Auth**: None

---

## MongoDB Collections

### `users`
- **Fields**: `username`, `email`, `password_hash`, `created_at`, `last_login_at`
- **Indexes**: `username` (unique)

### `projects`
- **Fields**: `project_id`, `name`, `description`, `created_at`, `created_by`, `updated_at`, `updated_by`
- **Indexes**: `project_id` (unique)

### `project_members`
- **Fields**: `project_id`, `username`, `role`, `joined_at`
- **Indexes**: `project_id` + `username` (compound, unique)
- **Roles**: `manager`, `engineer`, `viewer`

---

## Notes

1. **Roles**: User accounts don't have roles. Roles are assigned per project via `project_members` collection.
2. **Admin Role**: Only the `admin` user account has a role field (for system-level permissions).
3. **Permissions**:
   - **Admin**: Can do everything
   - **Project Manager**: Can manage project and members
   - **Engineer**: Can upload configs/documents
   - **Viewer**: Read-only access
4. **MongoDB Connection**: Uses Motor (async MongoDB driver) with retry logic on startup.
5. **Docker**: MongoDB runs in container `mnp-mongo` on port 27017.

