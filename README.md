# Task Manager API

Production-ready asynchronous REST API for task management with JWT authentication. Built with FastAPI, PostgreSQL, SQLAlchemy, Docker.

## Features

- User registration & JWT authentication
- Create, read, delete tasks (private per user)
- Fully asynchronous (FastAPI + async SQLAlchemy + asyncpg)
- PostgreSQL database (Docker)
- Interactive API docs (Swagger UI)
- Docker support

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0 (async)
- JWT (python-jose)
- Pytest
- Docker

## Installation

### Prerequisites

- Python 3.11+
- Docker
- Git

### Setup

1. Clone the repository

   git clone https://github.com/NemesisYN/task-manager-api.git
   cd task-manager-api

2. Create and activate virtual environment

   python -m venv venv
   source venv/bin/activate    # Linux/Mac
   venv\Scripts\activate       # Windows

3. Install dependencies

   pip install -r requirements.txt

4. Create `.env` file

   SECRET_KEY=your_super_secret_key_here
   DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/postgres

5. Run PostgreSQL via Docker

   docker run --name my_postgres -e POSTGRES_PASSWORD=your_password -d -p 5432:5432 -v postgres_data:/var/lib/postgresql/data postgres:15

6. Start server

   uvicorn main:app --reload

7. Open API documentation

   http://localhost:8000/docs

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register new user |
| POST | /auth/login | Login and get JWT token |

### Tasks (protected)

Add header: `Authorization: Bearer <your_token>`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /tasks | Create task |
| GET | /tasks | List all tasks |
| GET | /tasks/{id} | Get task by ID |
| DELETE | /tasks/{id} | Delete task |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Check API status |

## Running Tests

pytest tests/test_main.py -v

Note: On Windows some tests may fail due to asyncio issues. Core functionality works on Linux/macOS.

## Docker Deployment

### Dockerfile

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

### docker-compose.yml

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:your_password@db:5432/postgres
      SECRET_KEY: your_super_secret_key

volumes:
  postgres_data:

### Run

docker-compose up --build

## Project Structure

my-first-api/
├── main.py
├── tests/
│   └── test_main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
├── .gitignore
└── README.md

## Environment Variables

Create `.env` file:

SECRET_KEY=your_super_secret_key
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/postgres

Never commit `.env` to repository.

## Author

Nikita – https://github.com/NemesisYN

## License

Educational and portfolio purposes only.