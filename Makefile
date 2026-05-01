# Operational shortcuts. Each target is a thin wrapper around scripts
# in scripts/ and infra/ — no hidden logic so the commands shown in the
# demo are the real ones.

PY ?= python3
AWS_REGION ?= us-east-1

export AWS_REGION

.PHONY: help install init-db init-images init-all run-local \
        deploy-frontend deploy-ecs deploy-lambda

help:
	@echo "Targets:"
	@echo "  install         pip install requirements.txt"
	@echo "  init-db         create login + music tables, seed users, load songs"
	@echo "  init-images     download artist images and upload to S3"
	@echo "  init-all        init-db + init-images"
	@echo "  run-local       run the Flask backend on localhost:8080"
	@echo "  deploy-frontend  deploy_frontend.sh \$$BUCKET"
	@echo "  deploy-ecs       build + push image to ECR"
	@echo "  deploy-lambda    sam build + deploy"

install:
	$(PY) -m pip install -r requirements.txt

init-db:
	$(PY) scripts/create_login_table.py
	$(PY) scripts/create_music_table.py
	$(PY) scripts/load_music_data.py

init-images:
	$(PY) scripts/upload_artist_images.py

init-all: init-db init-images

run-local:
	cd backend-ec2 && $(PY) app.py

deploy-frontend:
	@test -n "$$BUCKET" || (echo "BUCKET=name required" && exit 2)
	./infra/deploy_frontend.sh "$$BUCKET"

deploy-ecs:
	./backend-ecs/deploy.sh music-app

deploy-lambda:
	./backend-lambda/deploy.sh music-app-serverless
