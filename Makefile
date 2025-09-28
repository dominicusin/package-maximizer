.PHONY: help install test lint format clean build docker run

help: ## Показать это сообщение помощи
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt
	pip install -e .

install-dev: ## Установить зависимости для разработки
	pip install -r requirements.txt
	pip install -e ".[dev,all,web]"

test: ## Запустить тесты
	pytest tests/ -v --cov=package_maximizer --cov-report=html --cov-report=term

lint: ## Проверить код линтерами
	flake8 package_maximizer/ tests/
	mypy package_maximizer/ --ignore-missing-imports

format: ## Отформатировать код
	black package_maximizer/ tests/
	isort package_maximizer/ tests/

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/
	rm -rf .pytest_cache/

build: ## Собрать пакет
	python -m build

docker-build: ## Собрать Docker образ
	docker build -t package-maximizer:latest .

docker-run: ## Запустить в Docker
	docker run -p 5000:5000 package-maximizer:latest

run-web: ## Запустить веб-интерфейс
	python -m package_maximizer.web.app

init-config: ## Создать файл конфигурации по умолчанию
	package-maximizer init-config

all: lint test build ## Выполнить все проверки и сборку
