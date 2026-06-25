SHELL := /bin/bash

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
ALEMBIC ?= .venv/bin/alembic
SAM ?= sam
UVICORN ?= .venv/bin/uvicorn
APP ?= app.main:app
HOST ?= 127.0.0.1
PORT ?= 8000

AWS_REGION ?= us-east-1
STACK_NAME ?= knight-email-intake-service
TEMPLATE ?= template.yaml
S3_BUCKET ?=
DATABASE_URL ?=
VPC_SUBNET_IDS ?=
VPC_SECURITY_GROUP_IDS ?=
SAM_BUILD_ARGS ?= --use-container
SAM_DEPLOY_ARGS ?= --resolve-s3 --no-confirm-changeset --no-fail-on-empty-changeset
SAM_GUIDED_ARGS ?= --guided

.PHONY: help install dev local-env local-migrate validate build migrate aws-deploy aws-deploy-public aws-deploy-private deploy deploy-public deploy-private deploy-public-guided deploy-private-guided package-info delete clean check-local-database-url check-aws-env check-database-url check-s3-bucket check-vpc-env
.NOTPARALLEL: aws-deploy aws-deploy-public aws-deploy-private

help:
	@echo "Local targets:"
	@echo "  make install         Install Python dependencies into .venv"
	@echo "  make dev             Run local migrations and start FastAPI locally"
	@echo "  make local-migrate   Run Alembic migrations using .env/local DATABASE_URL"
	@echo ""
	@echo "AWS deployment targets:"
	@echo "  make aws-deploy-private  Validate, build, migrate RDS, and deploy Lambda in VPC"
	@echo "  make aws-deploy-public   Validate, build, migrate RDS, and deploy Lambda without VPC"
	@echo "  make aws-deploy          Alias for aws-deploy-private"
	@echo "  make validate        Validate the SAM template"
	@echo "  make build           Build Lambda package with SAM"
	@echo "  make migrate         Run Alembic migrations against DATABASE_URL"
	@echo "  make deploy-public   Deploy without Lambda VPC config"
	@echo "  make deploy-private  Deploy with VPC_SUBNET_IDS and VPC_SECURITY_GROUP_IDS"
	@echo "  make deploy-public-guided   Interactive public-RDS deploy"
	@echo "  make deploy-private-guided  Interactive private-RDS deploy"
	@echo "  make deploy          Alias for deploy-private"
	@echo "  make delete          Delete the SAM stack"
	@echo "  make clean           Remove SAM build output and Python caches"
	@echo ""
	@echo "Required for AWS deploy:"
	@echo "  DATABASE_URL='postgresql+psycopg://user:pass@rds-endpoint:5432/email_intake?sslmode=require'"
	@echo "  S3_BUCKET='email-intake-submissions'"
	@echo "  AWS_REGION='us-east-1'"
	@echo ""
	@echo "Required for private RDS deploy:"
	@echo "  VPC_SUBNET_IDS='subnet-abc123,subnet-def456'"
	@echo "  VPC_SECURITY_GROUP_IDS='sg-abc123'"

install:
	$(PIP) install -r requirements.txt

dev: local-env local-migrate
	$(UVICORN) $(APP) --reload --host $(HOST) --port $(PORT)

local-env:
	@test -f .env || cp .env.example .env

local-migrate: local-env check-local-database-url
	@set -a; source .env; set +a; $(ALEMBIC) upgrade head

validate:
	$(SAM) validate --template-file $(TEMPLATE) --lint

build:
	$(SAM) build --template-file $(TEMPLATE) $(SAM_BUILD_ARGS)

migrate: check-database-url
	@DATABASE_URL="$(DATABASE_URL)" $(ALEMBIC) upgrade head

deploy: deploy-private

aws-deploy: aws-deploy-private

aws-deploy-public: check-aws-env validate build migrate deploy-public

aws-deploy-private: check-aws-env check-vpc-env validate build migrate deploy-private

deploy-public: check-aws-env
	@$(SAM) deploy $(SAM_DEPLOY_ARGS) \
		--template-file .aws-sam/build/template.yaml \
		--stack-name "$(STACK_NAME)" \
		--region "$(AWS_REGION)" \
		--capabilities CAPABILITY_IAM \
		--parameter-overrides \
			DatabaseUrl="$(DATABASE_URL)" \
			S3Bucket="$(S3_BUCKET)"

deploy-private: check-aws-env check-vpc-env
	@$(SAM) deploy $(SAM_DEPLOY_ARGS) \
		--template-file .aws-sam/build/template.yaml \
		--stack-name "$(STACK_NAME)" \
		--region "$(AWS_REGION)" \
		--capabilities CAPABILITY_IAM \
		--parameter-overrides \
			DatabaseUrl="$(DATABASE_URL)" \
			S3Bucket="$(S3_BUCKET)" \
			VpcSubnetIds="$(VPC_SUBNET_IDS)" \
			VpcSecurityGroupIds="$(VPC_SECURITY_GROUP_IDS)"

deploy-public-guided: SAM_DEPLOY_ARGS=$(SAM_GUIDED_ARGS)
deploy-public-guided: deploy-public

deploy-private-guided: SAM_DEPLOY_ARGS=$(SAM_GUIDED_ARGS)
deploy-private-guided: deploy-private

package-info:
	@echo "STACK_NAME=$(STACK_NAME)"
	@echo "AWS_REGION=$(AWS_REGION)"
	@echo "S3_BUCKET=$(S3_BUCKET)"
	@echo "DATABASE_URL=$$(test -n "$(DATABASE_URL)" && echo '<set>' || echo '<missing>')"
	@echo "VPC_SUBNET_IDS=$$(test -n "$(VPC_SUBNET_IDS)" && echo '<set>' || echo '<missing>')"
	@echo "VPC_SECURITY_GROUP_IDS=$$(test -n "$(VPC_SECURITY_GROUP_IDS)" && echo '<set>' || echo '<missing>')"

delete:
	$(SAM) delete --stack-name "$(STACK_NAME)" --region "$(AWS_REGION)"

clean:
	rm -rf .aws-sam
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

check-local-database-url:
	@set -a; source .env; set +a; test -n "$$DATABASE_URL" || (echo "DATABASE_URL is required in .env"; exit 1)

check-aws-env: check-database-url check-s3-bucket

check-database-url:
	@test -n "$(DATABASE_URL)" || (echo "DATABASE_URL is required"; exit 1)

check-s3-bucket:
	@test -n "$(S3_BUCKET)" || (echo "S3_BUCKET is required"; exit 1)

check-vpc-env:
	@test -n "$(VPC_SUBNET_IDS)" || (echo "VPC_SUBNET_IDS is required for deploy-private"; exit 1)
	@test -n "$(VPC_SECURITY_GROUP_IDS)" || (echo "VPC_SECURITY_GROUP_IDS is required for deploy-private"; exit 1)
