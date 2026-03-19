import goz


def test_hello():
    assert goz.hello() == "Hello, world!"
    assert goz.hello("PyPI") == "Hello, PyPI!"


def test_version():
    assert goz.__version__ == "0.0.1"
