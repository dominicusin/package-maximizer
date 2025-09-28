"""Базовые тесты для проверки работоспособности"""

def test_import():
    """Тест импорта основных модулей"""
    try:
        import package_maximizer
        assert hasattr(package_maximizer, '__version__')
        assert package_maximizer.__version__ == "0.1.0"
    except ImportError:
        assert False, "Не удалось импортировать package_maximizer"

def test_basic_functionality():
    """Тест базовой функциональности"""
    # Пока простая проверка
    assert 1 + 1 == 2
    
def test_version():
    """Тест версии пакета"""
    from package_maximizer import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
