# Test Hello Package
import pytest
from src.hello import hello, goodbye

def test_hello():
    assert hello("Test") == "Hello, Test!"

def test_hello_default():
    assert hello() == "Hello, World!"

def test_goodbye():
    assert goodbye("Test") == "Goodbye, Test!"
