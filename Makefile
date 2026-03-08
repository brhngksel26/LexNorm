.PHONY: build up logs debug create-db migrate

NAME = lexnorm-app-1
DB_CONTAINER_NAME = lexnorm_database
DB_NAME= lexnorm

build:
	docker compose up -d --build

up:
	docker compose up -d

make logs:
	docker compose logs $(NAME) -f --tail 50

debug:
	docker attach $(NAME)

create-db:
	docker exec -it $(DB_CONTAINER_NAME) createdb -h 127.0.0.1 -U postgres $(DB_NAME)

makemigrations:
	docker exec -it $(NAME) alembic revision --autogenerate -m "$(message)"

migrate:
	docker exec -it $(NAME) alembic upgrade head

stamp:
	docker exec -it $(NAME) alembic stamp head

seed-users:
	docker exec -it $(NAME) python scripts/seed_users.py