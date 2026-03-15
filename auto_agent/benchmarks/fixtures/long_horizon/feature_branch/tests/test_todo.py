# Test Todo Functions
import pytest
from src.todo import TodoList, get_pending_items

def test_add_item():
    todo = TodoList()
    item = todo.add("Test task")
    assert item["title"] == "Test task"
    assert item["completed"] == False

def test_complete_item():
    todo = TodoList()
    todo.add("Test task")
    result = todo.complete(1)
    assert result == True
    
    items = todo.get_all()
    assert items[0]["completed"] == True

def test_get_pending_items():
    """This test SHOULD pass when bug is fixed"""
    todo = TodoList()
    todo.add("Buy groceries")
    todo.add("Walk the dog")
    todo.add("Finish project")
    
    # Mark first as complete
    todo.complete(1)
    
    # Should return items 2 and 3 (not completed)
    pending = get_pending_items(todo)
    
    pending_ids = [p["id"] for p in pending]
    assert 2 in pending_ids, "Item 2 should be pending"
    assert 3 in pending_ids, "Item 3 should be pending"
    assert 1 not in pending_ids, "Item 1 is completed, should not be in pending"
